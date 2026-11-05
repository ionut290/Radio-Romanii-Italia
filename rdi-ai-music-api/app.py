"""RDI AI MUSIC moderation API. Run behind HTTPS and a same-origin /api/ai-music/ reverse proxy."""
import os, sqlite3, secrets, hmac, subprocess, uuid, time, hashlib
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort

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
RATE_WINDOW_SECONDS=3600
RATE_MAX=6
VOTE_IP_DAILY_MAX=30

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
    columns={row["name"] for row in con.execute("PRAGMA table_info(submissions)").fetchall()}
    if "spotlight_consent" not in columns:
        con.execute("ALTER TABLE submissions ADD COLUMN spotlight_consent INTEGER NOT NULL DEFAULT 0")
    con.commit()
    return con
def now():
    return datetime.now(timezone.utc).isoformat()
def admin():
    supplied=request.headers.get("Authorization","")
    if not ADMIN_TOKEN or not hmac.compare_digest(supplied,"Bearer "+ADMIN_TOKEN):
        abort(401)
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
@app.post("/api/ai-music/submissions")
def submit():
    # Server must be behind HTTPS, with trusted proxy enforcing request limits.
    ip_key=rate_key()
    current=int(time.time())
    with db() as con:
        con.execute("DELETE FROM rate_events WHERE created_at<?",(current-RATE_WINDOW_SECONDS,))
        hits=con.execute("SELECT COUNT(*) FROM rate_events WHERE ip_key=? AND created_at>=?",(ip_key,current-RATE_WINDOW_SECONDS)).fetchone()[0]
        if hits>=RATE_MAX:
            return jsonify(error="Too many submissions. Retry later."),429
    if request.form.get("website"):  # honeypot
        return jsonify(ok=True),202
    artist=clamp(request.form.get("artist"),100)
    email=clamp(request.form.get("email"),200)
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
            con.execute("INSERT INTO submissions (id,created_at,artist,email,title,platform,link,notes,file_name,stored_name,spotlight_consent) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
              (sid,now(),artist,email,title,platform,link,notes,original,stored,spotlight_consent))
    except Exception:
        if stored:(FILES/stored).unlink(missing_ok=True)
        raise
    with db() as con:
        con.execute("INSERT INTO rate_events (ip_key,created_at) VALUES (?,?)",(ip_key,current))
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
    with db() as con:
        rows=con.execute("""
          SELECT s.id,s.artist,s.title,s.platform,s.link,s.created_at,
                 CASE WHEN s.spotlight_consent=1 AND s.stored_name IS NOT NULL THEN 1 ELSE 0 END AS audio_preview,
                 COUNT(v.submission_id) AS votes
          FROM submissions AS s
          LEFT JOIN spotlight_votes AS v ON v.submission_id=s.id
          WHERE s.status='approved'
          GROUP BY s.id
          ORDER BY votes DESC,s.created_at DESC LIMIT 200
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
    """One vote per browser identity and approved track, plus per-IP daily cap."""
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
    voter_key=hmac.new(ADMIN_TOKEN.encode(),visitor.lower().encode(),hashlib.sha256).hexdigest()
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

@app.get("/api/ai-music/health")
def health():
    return jsonify(ok=True,service="rdi-ai-music")
if __name__=="__main__":
    raise SystemExit("Use gunicorn behind a TLS-enabled reverse proxy; do not run a public Flask dev server.")
