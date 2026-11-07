"""RDI AI MUSIC moderation API. Run behind HTTPS and a same-origin /api/ai-music/ reverse proxy."""
import os, sqlite3, secrets, hmac, subprocess, uuid, time, hashlib, base64, smtplib, re, ssl
from email.message import EmailMessage
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort
try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport.requests import Request as GoogleAuthRequest
    GOOGLE_AUTH_LIBRARY_READY=True
except ImportError:
    google_id_token=None
    GoogleAuthRequest=None
    GOOGLE_AUTH_LIBRARY_READY=False

ROOT=Path(os.environ.get("RDI_AI_DATA_DIR","/var/lib/rdi-ai-music")).resolve()
FILES=ROOT/"uploads"
DB=ROOT/"submissions.sqlite3"
MAX_MB=int(os.environ.get("RDI_AI_MAX_MB","30"))
ADMIN_TOKEN=os.environ.get("RDI_AI_ADMIN_TOKEN","")
# Browser origins are exact matches; keep the API private until the reverse proxy is secured.
PUBLIC_ORIGIN=os.environ.get("RDI_AI_PUBLIC_ORIGIN","https://radioromanii.duckdns.org").rstrip("/")
ALLOWED_ORIGINS={PUBLIC_ORIGIN}
app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=MAX_MB*1024*1024+128*1024
ALLOWED_EXT={".mp3",".wav",".flac",".m4a",".ogg"}
# Permit a complete 10-track submission from one artist, with limited retry headroom.
# Keep the limit per IP to protect this publicly accessible upload endpoint.
RATE_WINDOW_SECONDS=max(60,int(os.environ.get("RDI_AI_SUBMISSION_RATE_WINDOW_SECONDS","3600")))
RATE_MAX=max(1,int(os.environ.get("RDI_AI_SUBMISSION_RATE_MAX","12")))
VOTE_IP_DAILY_MAX=30
# Enable only after SMTP delivery has been verified on the Oracle server.
AUTH_REQUIRED=os.environ.get("RDI_AI_REQUIRE_LOGIN","0").lower() in ("1","true","yes")
SMTP_HOST=os.environ.get("RDI_AI_SMTP_HOST","").strip()
SMTP_PORT=int(os.environ.get("RDI_AI_SMTP_PORT","587"))
SMTP_USER=os.environ.get("RDI_AI_SMTP_USER","").strip()
SMTP_PASSWORD=os.environ.get("RDI_AI_SMTP_PASSWORD","")
SMTP_FROM=os.environ.get("RDI_AI_SMTP_FROM","").strip()
SMTP_SSL=os.environ.get("RDI_AI_SMTP_SSL","0").lower() in ("1","true","yes")
AUTH_SECRET=os.environ.get("RDI_AI_AUTH_SECRET","") or ADMIN_TOKEN
AUTH_MAIL_READY=bool(SMTP_HOST and SMTP_FROM and AUTH_SECRET)
# Public OAuth client ID for the official RDI site (not a secret). An env override is supported.
GOOGLE_CLIENT_ID=os.environ.get("RDI_AI_GOOGLE_CLIENT_ID","952052945501-atbs3pg7n7v0gnjk50q75njg6i79nqnt.apps.googleusercontent.com").strip()
GOOGLE_AUTH_READY=bool(GOOGLE_CLIENT_ID and GOOGLE_AUTH_LIBRARY_READY)
AUTH_SESSION_SECONDS=14*86400
AUTH_CODE_SECONDS=10*60

def rate_key():
    # Nginx MUST overwrite X-Real-IP; otherwise all requests via Unix socket share one IP.
    ip=request.headers.get("X-Real-IP") or request.remote_addr or "unknown"
    salt=ADMIN_TOKEN or "rdi-ai-music"
    return hmac.new(salt.encode(),ip.encode(),hashlib.sha256).hexdigest()
def db():
    ROOT.mkdir(parents=True,exist_ok=True)
    FILES.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB,timeout=20)
    con.row_factory=sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS submissions (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL, artist TEXT NOT NULL,
      email TEXT NOT NULL, title TEXT NOT NULL, platform TEXT NOT NULL,
      link TEXT NOT NULL, notes TEXT NOT NULL, file_name TEXT,
      stored_name TEXT, status TEXT NOT NULL DEFAULT 'pending',
      reviewed_at TEXT, reviewed_note TEXT NOT NULL DEFAULT '')""")
    con.execute("CREATE TABLE IF NOT EXISTS rate_events (ip_key TEXT NOT NULL, created_at INTEGER NOT NULL)")
    con.execute("CREATE INDEX IF NOT EXISTS rate_events_by_ip ON rate_events(ip_key, created_at)")
    con.execute("""CREATE TABLE IF NOT EXISTS spotlight_votes (
      submission_id TEXT NOT NULL, voter_key TEXT NOT NULL,
      ip_key TEXT NOT NULL, created_at INTEGER NOT NULL,
      PRIMARY KEY(submission_id,voter_key))""")
    con.execute("CREATE INDEX IF NOT EXISTS spotlight_votes_by_ip ON spotlight_votes(ip_key,created_at)")
    con.execute("""CREATE TABLE IF NOT EXISTS spotlight_comments (
      id TEXT PRIMARY KEY, submission_id TEXT NOT NULL, nickname TEXT NOT NULL,
      body TEXT NOT NULL, created_at TEXT NOT NULL, created_epoch INTEGER NOT NULL,
      ip_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'visible')""")
    con.execute("CREATE INDEX IF NOT EXISTS spotlight_comments_by_track ON spotlight_comments(submission_id,status,created_epoch)")
    con.execute("CREATE INDEX IF NOT EXISTS spotlight_comments_by_ip ON spotlight_comments(ip_key,created_epoch)")
    columns={row["name"] for row in con.execute("PRAGMA table_info(submissions)").fetchall()}
    if "spotlight_consent" not in columns:
        con.execute("ALTER TABLE submissions ADD COLUMN spotlight_consent INTEGER NOT NULL DEFAULT 0")
    con.execute("CREATE TABLE IF NOT EXISTS admin_settings (setting TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS admin_sessions (session_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS admin_login_attempts (ip_key TEXT NOT NULL, created_at INTEGER NOT NULL)")
    con.execute("CREATE INDEX IF NOT EXISTS admin_login_attempts_ip ON admin_login_attempts(ip_key,created_at)")
    if "user_id" not in columns:
        con.execute("ALTER TABLE submissions ADD COLUMN user_id TEXT DEFAULT NULL")
    con.execute("""CREATE TABLE IF NOT EXISTS music_users (
      id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, created_at TEXT NOT NULL)""")
    user_columns={row["name"] for row in con.execute("PRAGMA table_info(music_users)")}
    if "google_sub" not in user_columns:
        con.execute("ALTER TABLE music_users ADD COLUMN google_sub TEXT")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS music_google_sub_unique ON music_users(google_sub)")
    con.execute("""CREATE TABLE IF NOT EXISTS music_google_login_requests (
      ip_key TEXT NOT NULL, created_at INTEGER NOT NULL)""")
    con.execute("CREATE INDEX IF NOT EXISTS music_google_login_by_ip ON music_google_login_requests(ip_key,created_at)")
    con.execute("""CREATE TABLE IF NOT EXISTS music_login_codes (
      email TEXT PRIMARY KEY, code_hash TEXT NOT NULL, display_name TEXT NOT NULL,
      expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS music_login_requests (
      ip_key TEXT NOT NULL, email_hash TEXT NOT NULL, created_at INTEGER NOT NULL)""")
    con.execute("CREATE INDEX IF NOT EXISTS music_login_requests_ip ON music_login_requests(ip_key,created_at)")
    con.execute("""CREATE TABLE IF NOT EXISTS music_user_sessions (
      session_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL)""")
    con.execute("CREATE INDEX IF NOT EXISTS music_user_sessions_user ON music_user_sessions(user_id,expires_at)")
    con.commit()
    return con
def now():
    return datetime.now(timezone.utc).isoformat()
def admin():
    supplied=request.headers.get("Authorization","")
    if not supplied.startswith("Bearer ") or not ADMIN_TOKEN:
        abort(401)
    credential=supplied[7:]
    # Existing machine/admin token remains supported for migration and backend jobs.
    if hmac.compare_digest(credential,ADMIN_TOKEN):
        return
    digest=hashlib.sha256(credential.encode()).hexdigest()
    with db() as con:
        row=con.execute("SELECT expires_at FROM admin_sessions WHERE session_hash=?",(digest,)).fetchone()
    if not row or row["expires_at"]<int(time.time()):
        abort(401)

def password_digest(password,salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),400000).hex()

@app.get("/api/ai-music/admin/auth-status")
def admin_auth_status():
    with db() as con:
        exists=con.execute("SELECT 1 FROM admin_settings WHERE setting='password_hash'").fetchone()
    return jsonify(password_configured=bool(exists))

@app.post("/api/ai-music/admin/setup-password")
def admin_setup_password():
    if request.content_length and request.content_length>4096:
        return jsonify(error="Request too large"),413
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error="Invalid request"),400
    old_token=data.get("current_token")
    password=data.get("password")
    if not ADMIN_TOKEN or not isinstance(old_token,str) or not hmac.compare_digest(old_token,ADMIN_TOKEN):
        return jsonify(error="Administrator verification failed"),401
    if not isinstance(password,str) or len(password)<12 or len(password)>128:
        return jsonify(error="Use a password of 12-128 characters"),400
    salt=secrets.token_hex(16)
    digest=password_digest(password,salt)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        existing=con.execute("SELECT 1 FROM admin_settings WHERE setting='password_hash'").fetchone()
        if existing:
            return jsonify(error="Password already configured"),409
        con.execute("INSERT INTO admin_settings(setting,value) VALUES ('password_salt',?)",(salt,))
        con.execute("INSERT INTO admin_settings(setting,value) VALUES ('password_hash',?)",(digest,))
        con.commit()
    return jsonify(ok=True),201

@app.post("/api/ai-music/admin/login")
def admin_login():
    if request.content_length and request.content_length>4096:
        return jsonify(error="Request too large"),413
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or not isinstance(data.get("password"),str):
        return jsonify(error="Password required"),400
    password=data["password"]
    if len(password)>128:
        return jsonify(error="Invalid credentials"),401
    current=int(time.time())
    key=rate_key()
    con=db()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM admin_login_attempts WHERE created_at<?",(current-900,))
        attempts=con.execute("SELECT COUNT(*) FROM admin_login_attempts WHERE ip_key=?",(key,)).fetchone()[0]
        if attempts>=5:
            return jsonify(error="Too many attempts. Retry in 15 minutes"),429
        con.execute("INSERT INTO admin_login_attempts(ip_key,created_at) VALUES (?,?)",(key,current))
        con.commit()
        entries=dict(con.execute("SELECT setting,value FROM admin_settings WHERE setting IN ('password_salt','password_hash')").fetchall())
    finally:
        con.close()
    if not entries.get("password_hash") or not entries.get("password_salt"):
        return jsonify(error="Password setup required"),409
    digest=password_digest(password,entries["password_salt"])
    if not hmac.compare_digest(digest,entries["password_hash"]):
        return jsonify(error="Invalid credentials"),401
    session=secrets.token_urlsafe(32)
    expires=current+12*3600
    with db() as con:
        con.execute("INSERT INTO admin_sessions(session_hash,expires_at) VALUES (?,?)",(hashlib.sha256(session.encode()).hexdigest(),expires))
    return jsonify(ok=True,session=session,expires_at=expires)

@app.post("/api/ai-music/admin/logout")
def admin_logout():
    supplied=request.headers.get("Authorization","")
    if supplied.startswith("Bearer "):
        with db() as con:
            con.execute("DELETE FROM admin_sessions WHERE session_hash=?",(hashlib.sha256(supplied[7:].encode()).hexdigest(),))
    return jsonify(ok=True)
def clamp(value,limit):
    return str(value or "").strip()[:limit]
def valid_link(url):
    from urllib.parse import urlsplit
    p=urlsplit(url)
    return p.scheme=="https" and bool(p.hostname) and not p.username and not p.password
@app.before_request
def check_browser_origin():
    # Forms and admin calls may be cross-origin because the public site runs on
    # GitHub Pages and the API will run on the Oracle/AzuraCast HTTPS host.
    # Requests without Origin (for example curl and internal jobs) are permitted.
    origin=request.headers.get("Origin")
    if origin and origin not in ALLOWED_ORIGINS:
        abort(403)
    if request.method=="OPTIONS":
        return "",204

@app.after_request
def response_headers(r):
    origin=request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        r.headers["Access-Control-Allow-Origin"]=origin
        r.headers["Access-Control-Allow-Methods"]="GET, POST, OPTIONS"
        r.headers["Access-Control-Allow-Headers"]="Authorization, Content-Type"
        r.headers["Access-Control-Max-Age"]="600"
        r.headers["Vary"]="Origin"
    r.headers["Cache-Control"]="no-store"
    r.headers["X-Content-Type-Options"]="nosniff"
    r.headers["Referrer-Policy"]="no-referrer"
    return r

def music_email(value):
    value=str(value or "").strip().lower()
    if len(value)>254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}",value):
        return None
    if ".." in value or any(part.startswith("-") or part.endswith("-") for part in value.split("@")[-1].split(".")):
        return None
    return value

def send_music_login_email(email,code):
    if not AUTH_MAIL_READY:
        raise RuntimeError("Email login is not configured")
    message=EmailMessage()
    message["Subject"]="Il tuo codice di accesso RDI AI MUSIC"
    message["From"]=SMTP_FROM
    message["To"]=email
    message.set_content("Codice di accesso a Radio Românii din Italia AI MUSIC: "+code+"\n"
                        "Valido per 10 minuti. Non condividerlo con nessuno.\n"
                        "Se non lo hai richiesto, ignora questo messaggio.")
    if SMTP_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST,SMTP_PORT,timeout=12,context=ssl.create_default_context()) as smtp:
            if SMTP_USER: smtp.login(SMTP_USER,SMTP_PASSWORD)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=12) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if SMTP_USER: smtp.login(SMTP_USER,SMTP_PASSWORD)
            smtp.send_message(message)

def user_session(required=None):
    """Validate an RDI member session; never accept admin tokens as user sessions."""
    if required is None: required=AUTH_REQUIRED
    bearer=request.headers.get("Authorization","")
    if not bearer.startswith("Bearer "):
        return None if not required else (None, (jsonify(error="Login required"),401))
    token=bearer[7:]
    if len(token)>200 or not re.fullmatch(r"[A-Za-z0-9_-]{32,200}",token):
        return None if not required else (None, (jsonify(error="Invalid session"),401))
    session_hash=hashlib.sha256(token.encode()).hexdigest()
    with db() as con:
        row=con.execute("""SELECT u.id,u.email,u.display_name
            FROM music_user_sessions ms JOIN music_users u ON u.id=ms.user_id
            WHERE ms.session_hash=? AND ms.expires_at>=?""",
            (session_hash,int(time.time()))).fetchone()
    if row: return dict(row)
    return None if not required else (None, (jsonify(error="Session expired or invalid"),401))

def require_music_user():
    result=user_session(required=True)
    if isinstance(result,tuple): return None,result[1]
    return result,None

@app.get("/api/ai-music/auth/config")
def music_auth_config():
    return jsonify(login_required=AUTH_REQUIRED,email_available=AUTH_MAIL_READY,
                   google_available=GOOGLE_AUTH_READY,
                   google_client_id=GOOGLE_CLIENT_ID if GOOGLE_AUTH_READY else None,
                   providers=["email_code","google"] if GOOGLE_AUTH_READY else ["email_code"],
                   provider="email_code")


def verify_google_credential(credential,nonce):
    """Validate Google's signed ID token, issuer, audience, expiry and nonce."""
    if not GOOGLE_AUTH_READY:
        raise RuntimeError("Google login is not configured")
    try:
        claims=google_id_token.verify_oauth2_token(
            credential,GoogleAuthRequest(),GOOGLE_CLIENT_ID)
    except ValueError as exc:
        # Do not expose the token or the verifier's detailed error in responses.
        raise ValueError("Google identity token could not be verified") from exc
    except Exception as exc:
        raise RuntimeError("Google identity provider temporarily unavailable") from exc
    if claims.get("iss") not in ("accounts.google.com","https://accounts.google.com"):
        raise ValueError("Invalid Google token issuer")
    if claims.get("aud")!=GOOGLE_CLIENT_ID:
        raise ValueError("Invalid Google token audience")
    if not hmac.compare_digest(str(claims.get("nonce","")),nonce):
        raise ValueError("Google login nonce mismatch")
    if claims.get("email_verified") not in (True,"true"):
        raise ValueError("Google email is not verified")
    email=music_email(claims.get("email"))
    sub=claims.get("sub")
    if not email or not isinstance(sub,str) or not 5<=len(sub)<=255:
        raise ValueError("Invalid Google account")
    # Google is authoritative for Gmail and Google Workspace mailboxes.
    # Avoid taking over existing email-code accounts using external mailbox
    # addresses that Google may have verified only once in the past.
    domain=email.rsplit("@",1)[-1]
    hosted=claims.get("hd")
    authoritative=(domain in ("gmail.com","googlemail.com") or
                   (isinstance(hosted,str) and hosted.lower()==domain))
    if not authoritative:
        raise ValueError("Use a Gmail or verified Google Workspace address")
    return email,sub,clamp(claims.get("name") or claims.get("given_name"),40) or "Artista RDI"

@app.post("/api/ai-music/auth/google")
def music_auth_google():
    """Google Identity Services: exchange a VERIFIED ID token for an RDI session."""
    if request.headers.get("Origin")!=PUBLIC_ORIGIN:
        return jsonify(error="Please use the RDI website"),403
    if not GOOGLE_AUTH_READY:
        return jsonify(error="Google login not configured on RDI"),503
    if request.content_length and request.content_length>8192:
        return jsonify(error="Request too large"),413
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error="JSON required"),400
    credential=data.get("credential")
    nonce=data.get("nonce")
    if not isinstance(credential,str) or not 50<=len(credential)<=6144:
        return jsonify(error="Invalid Google credential"),400
    if not isinstance(nonce,str) or not 20<=len(nonce)<=128 or not re.fullmatch(r"[A-Za-z0-9_-]+",nonce):
        return jsonify(error="Invalid login request"),400
    ip_key=rate_key()
    current=int(time.time())
    with db() as con:
        con.execute("DELETE FROM music_google_login_requests WHERE created_at<?",(current-3600,))
        hits=con.execute("SELECT COUNT(*) FROM music_google_login_requests WHERE ip_key=?",
                         (ip_key,)).fetchone()[0]
        if hits>=30:
            return jsonify(error="Too many login attempts. Please try later."),429
        con.execute("INSERT INTO music_google_login_requests(ip_key,created_at) VALUES(?,?)",
                    (ip_key,current))
    try:
        email,sub,name=verify_google_credential(credential,nonce)
    except ValueError as exc:
        return jsonify(error=str(exc)),401
    except Exception:
        app.logger.exception("Google credential verification unavailable")
        return jsonify(error="Google verification unavailable. Try again later."),503
    token=secrets.token_urlsafe(36)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        account=con.execute("SELECT id,email,google_sub FROM music_users WHERE google_sub=?",
                            (sub,)).fetchone()
        if account is not None:
            user_id=account["id"]
        else:
            account=con.execute("SELECT id,email,google_sub FROM music_users WHERE email=?",
                                (email,)).fetchone()
            if account is not None and account["google_sub"] not in (None,sub):
                return jsonify(error="This email belongs to another Google account"),409
            if account is not None:
                user_id=account["id"]
                con.execute("UPDATE music_users SET google_sub=? WHERE id=?",(sub,user_id))
            else:
                user_id=uuid.uuid4().hex
                con.execute("""INSERT INTO music_users(id,email,display_name,created_at,google_sub)
                            VALUES(?,?,?,?,?)""",(user_id,email,name,now(),sub))
        # Preserve earlier uploads made using the same verified email address.
        con.execute("UPDATE submissions SET user_id=? WHERE user_id IS NULL AND lower(email)=?",
                    (user_id,email))
        con.execute("INSERT INTO music_user_sessions(session_hash,user_id,expires_at) VALUES(?,?,?)",
                    (hashlib.sha256(token.encode()).hexdigest(),user_id,
                     current+AUTH_SESSION_SECONDS))
        con.execute("DELETE FROM music_user_sessions WHERE expires_at<?",(current,))
    with db() as con:
        user=dict(con.execute("SELECT id,email,display_name FROM music_users WHERE id=?",
                              (user_id,)).fetchone())
    return jsonify(ok=True,session=token,user=user,expires_in_seconds=AUTH_SESSION_SECONDS),200

@app.post("/api/ai-music/auth/request-code")
def music_auth_request_code():
    if request.headers.get("Origin")!=PUBLIC_ORIGIN:
        return jsonify(error="Please use the RDI website"),403
    if not AUTH_MAIL_READY:
        return jsonify(error="Email login has not been configured yet"),503
    if request.content_length and request.content_length>2048:
        return jsonify(error="Request too large"),413
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict): return jsonify(error="JSON required"),400
    email=music_email(data.get("email"))
    display_name=clamp(data.get("name"),40)
    if not email: return jsonify(error="Enter a valid email address"),400
    current=int(time.time())
    ip_key=rate_key()
    email_hash=hashlib.sha256(email.encode()).hexdigest()
    with db() as con:
        con.execute("DELETE FROM music_login_requests WHERE created_at<?",(current-3600,))
        last=con.execute("SELECT MAX(created_at) FROM music_login_requests WHERE email_hash=?",
                         (email_hash,)).fetchone()[0]
        ip_hits=con.execute("SELECT COUNT(*) FROM music_login_requests WHERE ip_key=?",
                            (ip_key,)).fetchone()[0]
        email_hits=con.execute("SELECT COUNT(*) FROM music_login_requests WHERE email_hash=?",
                               (email_hash,)).fetchone()[0]
        if (last is not None and current-last<60) or ip_hits>=12 or email_hits>=5:
            return jsonify(error="Too many login attempts. Try again later."),429
        code=f"{secrets.randbelow(1000000):06d}"
        code_hash=hmac.new(AUTH_SECRET.encode(),
                           (email+":"+code).encode(),hashlib.sha256).hexdigest()
        con.execute("""INSERT OR REPLACE INTO music_login_codes(email,code_hash,display_name,expires_at,attempts)
            VALUES(?,?,?,?,0)""",(email,code_hash,display_name,current+AUTH_CODE_SECONDS))
        con.execute("INSERT INTO music_login_requests(ip_key,email_hash,created_at) VALUES(?,?,?)",
                    (ip_key,email_hash,current))
    try:
        send_music_login_email(email,code)
    except Exception:
        app.logger.exception("RDI login email delivery failed")
        with db() as con:
            con.execute("DELETE FROM music_login_codes WHERE email=? AND code_hash=?",(email,code_hash))
        return jsonify(error="Cannot send the email right now. Try again later."),503
    return jsonify(ok=True,message="Verification code sent",expires_in_seconds=AUTH_CODE_SECONDS)

@app.post("/api/ai-music/auth/verify-code")
def music_auth_verify_code():
    if request.headers.get("Origin")!=PUBLIC_ORIGIN:
        return jsonify(error="Please use the RDI website"),403
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict): return jsonify(error="JSON required"),400
    email=music_email(data.get("email"))
    code=data.get("code")
    if not email or not isinstance(code,str) or not re.fullmatch(r"\d{6}",code):
        return jsonify(error="Invalid verification code"),400
    current=int(time.time())
    token=secrets.token_urlsafe(36)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        row=con.execute("SELECT * FROM music_login_codes WHERE email=?",(email,)).fetchone()
        if not row or row["expires_at"]<current or row["attempts"]>=5:
            return jsonify(error="Code expired or invalid. Request a new code."),401
        expected=hmac.new(AUTH_SECRET.encode(),
                          (email+":"+code).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(row["code_hash"],expected):
            con.execute("UPDATE music_login_codes SET attempts=attempts+1 WHERE email=?",(email,))
            con.commit()
            return jsonify(error="Incorrect code"),401
        user=con.execute("SELECT id,email,display_name FROM music_users WHERE email=?",(email,)).fetchone()
        if user is None:
            user_id=uuid.uuid4().hex
            name=(row["display_name"] or "Utente RDI").strip()
            if len(name)<2: name="Utente RDI"
            con.execute("INSERT INTO music_users(id,email,display_name,created_at) VALUES(?,?,?,?)",
                        (user_id,email,name,now()))
        else:
            user_id=user["id"]
        # Link legacy submissions to the now-verified email owner.
        con.execute("UPDATE submissions SET user_id=? WHERE user_id IS NULL AND lower(email)=?",
                    (user_id,email))
        con.execute("DELETE FROM music_login_codes WHERE email=?",(email,))
        con.execute("INSERT INTO music_user_sessions(session_hash,user_id,expires_at) VALUES(?,?,?)",
                    (hashlib.sha256(token.encode()).hexdigest(),user_id,current+AUTH_SESSION_SECONDS))
        con.execute("DELETE FROM music_user_sessions WHERE expires_at<?",(current,))
    with db() as con:
        user=dict(con.execute("SELECT id,email,display_name FROM music_users WHERE id=?",(user_id,)).fetchone())
    return jsonify(ok=True,session=token,user=user,expires_in_seconds=AUTH_SESSION_SECONDS),200

@app.get("/api/ai-music/auth/me")
def music_auth_me():
    user,error=require_music_user()
    if error: return error
    return jsonify(user=user)

@app.post("/api/ai-music/auth/logout")
def music_auth_logout():
    bearer=request.headers.get("Authorization","")
    if bearer.startswith("Bearer "):
        with db() as con:
            con.execute("DELETE FROM music_user_sessions WHERE session_hash=?",
                        (hashlib.sha256(bearer[7:].encode()).hexdigest(),))
    return jsonify(ok=True)

@app.get("/api/ai-music/me/submissions")
def my_music_submissions():
    user,error=require_music_user()
    if error: return error
    with db() as con:
        rows=con.execute("""SELECT id,title,artist,platform,created_at,status
            FROM submissions WHERE user_id=? ORDER BY created_at DESC LIMIT 300""",
            (user["id"],)).fetchall()
    return jsonify(submissions=[dict(row) for row in rows])

@app.post("/api/ai-music/submissions")
def submit():
    # Secure member-only uploads when the RDI account system is activated.
    user,error=(require_music_user() if AUTH_REQUIRED else (None,None))
    if error: return error
    # Server must be behind HTTPS, with trusted proxy enforcing request limits.
    ip_key=rate_key()
    current=int(time.time())
    # Verified accounts have their own 12-track quota, while the IP safety cap
    # prevents unlimited new accounts from sending unlimited files.
    account_key=hmac.new((AUTH_SECRET or ADMIN_TOKEN).encode(),
                         ("member:"+user["id"]).encode(),hashlib.sha256).hexdigest() if user else ip_key
    with db() as con:
        con.execute("DELETE FROM rate_events WHERE created_at<?",(current-RATE_WINDOW_SECONDS,))
        hits=con.execute("SELECT COUNT(*) FROM rate_events WHERE ip_key=? AND created_at>=?",(account_key,current-RATE_WINDOW_SECONDS)).fetchone()[0]
        ip_hits=con.execute("SELECT COUNT(*) FROM rate_events WHERE ip_key=? AND created_at>=?",(ip_key,current-RATE_WINDOW_SECONDS)).fetchone()[0] if user else 0
        if hits>=RATE_MAX or (user and ip_hits>=60):
            limited_key=ip_key if (user and ip_hits>=60) else account_key
            oldest=con.execute(
                "SELECT MIN(created_at) FROM rate_events WHERE ip_key=? AND created_at>=?",
                (limited_key,current-RATE_WINDOW_SECONDS)
            ).fetchone()[0]
            retry_after=max(1,RATE_WINDOW_SECONDS-(current-int(oldest))) if oldest is not None else RATE_WINDOW_SECONDS
            response=jsonify(error="Too many submissions. Retry later.",
                             retry_after_seconds=retry_after)
            response.status_code=429
            response.headers["Retry-After"]=str(retry_after)
            return response
    if request.form.get("website"):  # honeypot
        return jsonify(ok=True),202
    artist=clamp(request.form.get("artist"),100)
    email=user["email"] if user else clamp(request.form.get("email"),200)
    title=clamp(request.form.get("title"),160)
    platform=clamp(request.form.get("platform"),60)
    link=clamp(request.form.get("link"),1500)
    notes=clamp(request.form.get("notes"),800)
    spotlight_consent=int(request.form.get("spotlight_consent")=="yes")
    if not artist or not title or not email or "@" not in email or not platform:
        return jsonify(error="Required fields missing"),400
    if link and not valid_link(link):
        return jsonify(error="A valid HTTPS link is required"),400
    if request.form.get("rights")!="yes" or request.form.get("privacy")!="yes":
        return jsonify(error="Required declarations missing"),400
    upload=request.files.get("audio")
    if not link and (not upload or not upload.filename):
        return jsonify(error="Provide a link or an audio file"),400
    sid=uuid.uuid4().hex
    stored=None
    original=None
    if upload and upload.filename:
        original=clamp(Path(upload.filename.replace("\\","/")).name,180)
        suffix=Path(original).suffix.lower()
        if suffix not in ALLOWED_EXT:
            return jsonify(error="Unsupported audio extension"),400
        stored=sid+suffix
        # First-ever upload must work even before a database read has initialized storage.
        FILES.mkdir(parents=True, exist_ok=True)
        location=FILES/stored
        size=0
        try:
            with open(location,"xb") as dst:
                while True:
                    chunk=upload.stream.read(1024*1024)
                    if not chunk: break
                    size+=len(chunk)
                    if size>MAX_MB*1024*1024:
                        raise ValueError("File too large")
                    dst.write(chunk)
            if not size: raise ValueError("Empty file")
        except (OSError,ValueError) as exc:
            location.unlink(missing_ok=True)
            return jsonify(error=str(exc)),400
    try:
        with db() as con:
            con.execute("INSERT INTO submissions (id,created_at,artist,email,title,platform,link,notes,file_name,stored_name,spotlight_consent,user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (sid,now(),artist,email,title,platform,link,notes,original,stored,spotlight_consent,user["id"] if user else None))
    except Exception:
        if stored:(FILES/stored).unlink(missing_ok=True)
        raise
    with db() as con:
        con.execute("INSERT INTO rate_events (ip_key,created_at) VALUES (?,?)",(account_key,current))
        if user: con.execute("INSERT INTO rate_events (ip_key,created_at) VALUES (?,?)",(ip_key,current))
    return jsonify(ok=True,id=sid,status="pending"),201
@app.get("/api/ai-music/admin/submissions")
def list_submissions():
    admin()
    with db() as con:
        rows=con.execute("SELECT id,created_at,artist,email,title,platform,link,notes,file_name,status,reviewed_at,reviewed_note,spotlight_consent FROM submissions ORDER BY created_at DESC LIMIT 300").fetchall()
    return jsonify(submissions=[dict(row) for row in rows])
@app.get("/api/ai-music/admin/submissions/<sid>/audio")
def audio(sid):
    admin()
    with db() as con:
        row=con.execute("SELECT stored_name,file_name FROM submissions WHERE id=?",(sid,)).fetchone()
    if not row or not row["stored_name"]: abort(404)
    path=FILES/row["stored_name"]
    if not path.is_file(): abort(404)
    return send_file(path,as_attachment=True,download_name=row["file_name"],mimetype="application/octet-stream")
@app.post("/api/ai-music/admin/submissions/<sid>/review")
def review(sid):
    admin()
    data=request.get_json(silent=True) or {}
    status=data.get("status")
    if status not in ("approved","rejected","pending"): return jsonify(error="Invalid status"),400
    note=clamp(data.get("note"),800)
    with db() as con:
        row=con.execute("SELECT stored_name FROM submissions WHERE id=?",(sid,)).fetchone()
        if not row: abort(404)
        if status=="approved" and row["stored_name"]:
            # Refuse a mislabeled file. Requires ffprobe from FFmpeg.
            try:
                p=subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_type","-of","default=nw=1",str(FILES/row["stored_name"])],capture_output=True,text=True,timeout=20)
                if p.returncode or "codec_type=audio" not in p.stdout:
                    return jsonify(error="Audio validation failed"),400
            except (OSError,subprocess.TimeoutExpired):
                return jsonify(error="ffprobe unavailable or timed out"),503
        con.execute("UPDATE submissions SET status=?,reviewed_at=?,reviewed_note=? WHERE id=?",(status,now(),note,sid))
    return jsonify(ok=True,status=status)

@app.post("/api/ai-music/admin/submissions/<sid>/spotlight-consent")
def update_spotlight_consent(sid):
    """Editors record verified artist consent; never infer it from radio approval."""
    admin()
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or type(data.get("enabled")) is not bool:
        return jsonify(error="Explicit enabled true/false required"),400
    enabled=data["enabled"]
    if enabled and data.get("artist_permission_confirmed") is not True:
        return jsonify(error="Confirm the artist explicitly authorized public playback"),400
    with db() as con:
        row=con.execute("SELECT stored_name,status FROM submissions WHERE id=?",(sid,)).fetchone()
        if not row:
            abort(404)
        if enabled and (not row["stored_name"] or row["status"]!="approved"):
            return jsonify(error="An approved uploaded audio file is required"),400
        con.execute("UPDATE submissions SET spotlight_consent=? WHERE id=?",(int(enabled),sid))
    return jsonify(ok=True,spotlight_consent=int(enabled))

@app.get("/api/ai-music/spotlight")
def spotlight():
    """Public ranking. Never expose submitter email, notes or private file paths."""
    try:
        page=max(1,min(int(request.args.get("page","1")),100000))
    except ValueError:
        page=1
    per_page=20
    with db() as con:
        total=con.execute("SELECT COUNT(*) FROM submissions WHERE status='approved'").fetchone()[0]
        rows=con.execute("""
          SELECT s.id,s.artist,s.title,s.platform,s.link,s.created_at,
                 CASE WHEN s.spotlight_consent=1 AND s.stored_name IS NOT NULL THEN 1 ELSE 0 END AS audio_preview,
                 COUNT(v.submission_id) AS votes
          FROM submissions AS s
          LEFT JOIN spotlight_votes AS v ON v.submission_id=s.id
          WHERE s.status='approved'
          GROUP BY s.id
          ORDER BY votes DESC,s.created_at DESC LIMIT ? OFFSET ?
        """,(per_page,(page-1)*per_page)).fetchall()
    return jsonify(tracks=[dict(row) for row in rows],page=page,per_page=per_page,total=total,total_pages=max(1,(total+per_page-1)//per_page))


@app.get("/api/ai-music/spotlight/playlist")
def spotlight_playlist():
    """Public queue of approved, consented uploaded audio only."""
    with db() as con:
        rows=con.execute("""
          SELECT s.id,s.title,s.artist FROM submissions s
          LEFT JOIN spotlight_votes v ON v.submission_id=s.id
          WHERE s.status='approved' AND s.spotlight_consent=1 AND s.stored_name IS NOT NULL
          GROUP BY s.id ORDER BY COUNT(v.submission_id) DESC,s.created_at DESC LIMIT 1000
        """).fetchall()
    return jsonify(tracks=[dict(row) for row in rows])

@app.get("/api/ai-music/spotlight/<sid>/audio")
def spotlight_audio(sid):
    """Public listen-only preview if the submitter consented and editors approved."""
    with db() as con:
        row=con.execute("SELECT stored_name FROM submissions WHERE id=? AND status='approved' AND spotlight_consent=1",(sid,)).fetchone()
    if not row or not row["stored_name"]:
        abort(404)
    path=FILES/row["stored_name"]
    if not path.is_file():
        abort(404)
    mime={".mp3":"audio/mpeg",".wav":"audio/wav",".flac":"audio/flac",".m4a":"audio/mp4",".ogg":"audio/ogg"}.get(path.suffix.lower(),"application/octet-stream")
    response=send_file(path,mimetype=mime,conditional=True)
    response.headers["Content-Disposition"]="inline"
    response.headers["X-Content-Type-Options"]="nosniff"
    return response

@app.post("/api/ai-music/spotlight/<sid>/vote")
def spotlight_vote(sid):
    """One vote per account and track when account access is required."""
    user,error=(require_music_user() if AUTH_REQUIRED else (None,None))
    if error: return error
    if request.headers.get("Origin")!=PUBLIC_ORIGIN:
        return jsonify(error="Voting is available on the RDI website only"),403
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error="JSON body required"),400
    visitor=data.get("visitor")
    if not isinstance(visitor,str) or len(visitor)!=36:
        return jsonify(error="Invalid visitor ID"),400
    try:
        visitor_uuid=uuid.UUID(visitor)
        if str(visitor_uuid)!=visitor.lower() or visitor_uuid.version!=4:
            raise ValueError()
    except (ValueError,AttributeError):
        return jsonify(error="Invalid visitor ID"),400
    if not ADMIN_TOKEN:
        return jsonify(error="Voting temporarily unavailable"),503
    identity=("user:"+user["id"]) if user else visitor.lower()
    voter_key=hmac.new(ADMIN_TOKEN.encode(),identity.encode(),hashlib.sha256).hexdigest()
    ip_key=rate_key()
    current=int(time.time())
    con=db()
    try:
        con.execute("BEGIN IMMEDIATE")
        approved=con.execute("SELECT 1 FROM submissions WHERE id=? AND status='approved'",(sid,)).fetchone()
        if not approved:
            return jsonify(error="Track unavailable"),404
        existing=con.execute("SELECT 1 FROM spotlight_votes WHERE submission_id=? AND voter_key=?",(sid,voter_key)).fetchone()
        if existing:
            return jsonify(error="Already voted for this track"),409
        recent=con.execute("SELECT COUNT(*) FROM spotlight_votes WHERE ip_key=? AND created_at>=?",(ip_key,current-86400)).fetchone()[0]
        if recent>=VOTE_IP_DAILY_MAX:
            return jsonify(error="Daily vote limit reached"),429
        con.execute("INSERT INTO spotlight_votes(submission_id,voter_key,ip_key,created_at) VALUES (?,?,?,?)",(sid,voter_key,ip_key,current))
        con.commit()
        votes=con.execute("SELECT COUNT(*) FROM spotlight_votes WHERE submission_id=?",(sid,)).fetchone()[0]
    finally:
        con.close()
    return jsonify(ok=True,votes=votes),201


@app.get("/api/ai-music/spotlight/<sid>/comments")
def spotlight_comments(sid):
    """Only public comments on approved tracks; no private commenter metadata."""
    with db() as con:
        approved=con.execute("SELECT 1 FROM submissions WHERE id=? AND status='approved'",(sid,)).fetchone()
        if not approved:
            return jsonify(error="Track unavailable"),404
        rows=con.execute("""SELECT id,nickname,body,created_at FROM spotlight_comments
            WHERE submission_id=? AND status='visible'
            ORDER BY created_epoch DESC,id DESC LIMIT 100""",(sid,)).fetchall()
    return jsonify(comments=[dict(row) for row in rows])

@app.post("/api/ai-music/spotlight/<sid>/comments")
def add_spotlight_comment(sid):
    """Account comments after activation, retaining the existing anti-abuse checks."""
    user,error=(require_music_user() if AUTH_REQUIRED else (None,None))
    if error: return error
    if request.headers.get("Origin")!=PUBLIC_ORIGIN:
        return jsonify(error="Comments must be submitted from the RDI website"),403
    if request.content_length and request.content_length>4096:
        return jsonify(error="Comment too large"),413
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error="JSON required"),400
    if data.get("website"):
        return jsonify(ok=True),202
    nickname=data.get("nickname")
    body=data.get("body")
    if not isinstance(nickname,str) or not isinstance(body,str):
        return jsonify(error="Name and comment are required"),400
    nickname=user["display_name"] if user else nickname.strip()
    body=body.strip()
    if not (2<=len(nickname)<=40) or not (3<=len(body)<=500):
        return jsonify(error="Name must be 2-40 characters and comment 3-500 characters"),400
    if any(ord(c)<32 and c not in "\\n\\t" for c in nickname+body):
        return jsonify(error="Invalid characters"),400
    if "http://" in body.lower() or "https://" in body.lower() or "www." in body.lower():
        return jsonify(error="Links are not allowed in comments"),400
    ip_key=rate_key()
    current=int(time.time())
    cid=uuid.uuid4().hex
    con=db()
    try:
        con.execute("BEGIN IMMEDIATE")
        approved=con.execute("SELECT 1 FROM submissions WHERE id=? AND status='approved'",(sid,)).fetchone()
        if not approved:
            return jsonify(error="Track unavailable"),404
        last=con.execute("SELECT MAX(created_epoch) FROM spotlight_comments WHERE ip_key=?",(ip_key,)).fetchone()[0]
        if last is not None and current-last<60:
            return jsonify(error="Please wait one minute before commenting again"),429
        recent=con.execute("SELECT COUNT(*) FROM spotlight_comments WHERE ip_key=? AND created_epoch>=?",(ip_key,current-86400)).fetchone()[0]
        if recent>=10:
            return jsonify(error="Daily comment limit reached"),429
        con.execute("""INSERT INTO spotlight_comments
            (id,submission_id,nickname,body,created_at,created_epoch,ip_key,status)
            VALUES (?,?,?,?,?,?,?,'visible')""",
            (cid,sid,nickname,body,now(),current,ip_key))
        con.commit()
    finally:
        con.close()
    return jsonify(ok=True,id=cid),201

@app.get("/api/ai-music/admin/spotlight/comments")
def admin_spotlight_comments():
    admin()
    with db() as con:
        rows=con.execute("""SELECT c.id,c.submission_id,c.nickname,c.body,c.created_at,
            c.status,s.title FROM spotlight_comments c JOIN submissions s ON s.id=c.submission_id
            ORDER BY c.created_epoch DESC LIMIT 300""").fetchall()
    return jsonify(comments=[dict(row) for row in rows])

@app.post("/api/ai-music/admin/spotlight/comments/<cid>/hide")
def admin_hide_spotlight_comment(cid):
    admin()
    with db() as con:
        result=con.execute("UPDATE spotlight_comments SET status='hidden' WHERE id=?",(cid,))
        if result.rowcount==0:
            abort(404)
    return jsonify(ok=True)

@app.get("/api/ai-music/health")
def health():
    return jsonify(ok=True,service="rdi-ai-music")
if __name__=="__main__":
    raise SystemExit("Use gunicorn behind a TLS-enabled reverse proxy; do not run a public Flask dev server.")
