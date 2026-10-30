#!/usr/bin/env bash
# Optional specialist 10-genre classifier; sample only, no AzuraCast mutation.
set -euo pipefail
test "$EUID" -eq 0 || { echo "Root required for isolated audio reader installation" >&2; exit 1; }
SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/rdi-music-dj
VENV="$APP/ai-venv"
install -d -m 755 "$APP/models" "$APP/models/ast-preprocessor"
install -m 644 "$SRC/scripts/rdi_music_genre_ai.py" "$APP/rdi_music_genre_ai.py"
install -m 644 "$SRC/scripts/rdi_ast_fbank.py" "$APP/rdi_ast_fbank.py"
install -m 644 "$SRC/scripts/rdi_music_dj.py" "$APP/rdi_music_dj.py"
install -m 644 "$SRC/scripts/rdi-music-dj.html" "$APP/rdi-music-dj.html"
install -m 644 "$SRC/models/ast-gtzan-q4.onnx" "$APP/models/ast-gtzan-q4.onnx"
install -m 644 "$SRC/models/ast-preprocessor/preprocessor_config.json" "$APP/models/ast-preprocessor/preprocessor_config.json"
echo 'e065d352521c32bf9ddda62c3b4aa9effab003533c0f0b367befaa7b68b0cd51  /opt/rdi-music-dj/models/ast-gtzan-q4.onnx' | sha256sum -c - >/dev/null
"$VENV/bin/python" -m pip install --only-binary=:all: --disable-pip-version-check \
 'transformers==4.48.3' >/dev/null
"$VENV/bin/python" - <<'PY'
import sys,numpy as np
sys.path.insert(0,"/opt/rdi-music-dj")
import rdi_music_genre_ai as g
g.verify_model()
from rdi_ast_fbank import ast_features
import onnxruntime as ort
vals=ast_features(np.zeros(32000,dtype=np.float32),g.PREPROCESSOR/"preprocessor_config.json")
assert vals.shape==(1,1024,128)
opts=ort.SessionOptions()
opts.intra_op_num_threads=1
model=ort.InferenceSession(str(g.MODEL),sess_options=opts,providers=["CPUExecutionProvider"])
y=model.run(None,{model.get_inputs()[0].name:vals.astype("float32")})[0]
assert np.asarray(y).shape==(1,10)
assert g.decide(y)["needs_review"]
print("AST_GENRE_ARM64_SELF_TEST=SUCCESS")
PY
install -m 644 "$SRC/oracle/rdi-music-genre-analyze.service" /etc/systemd/system/rdi-music-genre-analyze.service
install -m 644 "$SRC/oracle/rdi-music-genre-analyze.timer" /etc/systemd/system/rdi-music-genre-analyze.timer
systemctl daemon-reload
systemctl enable --now rdi-music-genre-analyze.timer
systemctl is-active --quiet rdi-music-genre-analyze.timer
runuser -u ubuntu -- env HOME=/home/ubuntu /usr/bin/python3 "$APP/rdi_music_dj.py" report >/dev/null
systemctl restart rdi-music-dj-web.service
systemctl is-active --quiet rdi-music-dj-web.service
echo "AST_GENRE_PILOT=INSTALLED_READ_ONLY"
echo "AST_GENRE_PLAYLIST_CHANGES=ZERO"
