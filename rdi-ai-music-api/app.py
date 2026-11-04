"""RDI AI MUSIC moderation API. Run behind HTTPS and a same-origin /api/ai-music/ reverse proxy."""
import os, sqlite3, secrets, hmac, subprocess, uuid, time
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort

ROOT=Path(os.environ.get("RDI_AI_DATA_DIR","/var/lib/rdi-ai-music")).resolve()
FILES=ROOT/"uploads"
DB=ROOT/"submissions.sqlite3"
MAX_MB=int(os.environ.get("RDI_AI_MAX_MB","30"))
ADMIN_TOKEN=os.environ.get("RDI_AI_ADMIN_TOKEN","")
app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=MAX_MB*1024*1024+128*1024
ALLOWED_EXT={".mp3",".wav",".flac",".m4a",".ogg"}
RATE={}
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
@app.after_request
def response_headers(r):
    r.headers["Cache-Control"]="no-store"
    r.headers["X-Content-Type-Options"]="nosniff"
    r.headers["Referrer-Policy"]="no-referrer"
    return r
@app.post("/api/ai-music/submissions")
def submit():
    # Server must be behind HTTPS, with trusted proxy enforcing request limits.
    ip=request.remote_addr or "unknown"
    current=time.monotonic()
    RATE[ip]=[v for v in RATE.get(ip,[]) if current-v<3600]
    if len(RATE[ip])>=6:
        return jsonify(error="Too many submissions. Retry later."),429
    if request.form.get("website"):  # honeypot
        return jsonify(ok=True),202
    artist=clamp(request.form.get("artist"),100)
    email=clamp(request.form.get("email"),200)
    title=clamp(request.form.get("title"),160)
    platform=clamp(request.form.get("platform"),60)
    link=clamp(request.form.get("link"),1500)
    notes=clamp(request.form.get("notes"),800)
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
            con.execute("INSERT INTO submissions (id,created_at,artist,email,title,platform,link,notes,file_name,stored_name) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (sid,now(),artist,email,title,platform,link,notes,original,stored))
    except Exception:
        if stored:(FILES/stored).unlink(missing_ok=True)
        raise
    RATE[ip].append(current)
    return jsonify(ok=True,id=sid,status="pending"),201
@app.get("/api/ai-music/admin/submissions")
def list_submissions():
    admin()
    with db() as con:
        rows=con.execute("SELECT id,created_at,artist,email,title,platform,link,notes,file_name,status,reviewed_at,reviewed_note FROM submissions ORDER BY created_at DESC LIMIT 300").fetchall()
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
@app.get("/api/ai-music/health")
def health():
    return jsonify(ok=True,service="rdi-ai-music")
if __name__=="__main__":
    raise SystemExit("Use gunicorn behind a TLS-enabled reverse proxy; do not run a public Flask dev server.")
