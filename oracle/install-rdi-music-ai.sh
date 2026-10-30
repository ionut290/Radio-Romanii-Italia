#!/usr/bin/env bash
# Install free CPU-only YAMNet ONNX for RDI's 100-song music sample.
# No AzuraCast credentials or playlist modifications.
set -euo pipefail
test "$EUID" -eq 0 || { echo "Run as root" >&2; exit 1; }
SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/rdi-music-dj
MODEL_DIR="$APP/models"
VENV="$APP/ai-venv"
install -d -m 755 "$APP" "$MODEL_DIR"
install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/rdi-music
install -m 644 "$SRC/scripts/rdi_music_ai.py" "$APP/rdi_music_ai.py"
install -m 644 "$SRC/scripts/rdi_music_dj.py" "$APP/rdi_music_dj.py"
install -m 644 "$SRC/scripts/rdi-music-dj.html" "$APP/rdi-music-dj.html"
install -m 644 "$SRC/models/yamnet.onnx" "$MODEL_DIR/yamnet.onnx"
install -m 644 "$SRC/models/yamnet_class_map.csv" "$MODEL_DIR/yamnet_class_map.csv"
install -m 644 "$SRC/models/LICENSE" "$MODEL_DIR/LICENSE"
echo 'd3835ffbbd4a1bb3e777f0ca217b5007907f5171dd5d17c4236b95b2af8f908e  /opt/rdi-music-dj/models/yamnet.onnx' | sha256sum -c - >/dev/null
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
# Isolated Python packages so existing AzuraCast, RDI web and scripts are unchanged.
"$VENV/bin/python" -m pip install --disable-pip-version-check --only-binary=:all: \
  'numpy>=1.24,<2' 'onnxruntime>=1.20,<1.32' >/dev/null
# Load and execute a short safe synthetic waveform to ensure ARM compatibility.
"$VENV/bin/python" - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,"/opt/rdi-music-dj")
import rdi_music_ai as ai
ai.model_integrity()
names=ai.class_names()
import numpy as np
import onnxruntime as ort
opts=ort.SessionOptions()
opts.intra_op_num_threads=1
opts.inter_op_num_threads=1
session=ort.InferenceSession(str(ai.MODEL),sess_options=opts,providers=["CPUExecutionProvider"])
res=session.run(["output_0"],{"waveform":np.zeros(32000,dtype=np.float32)})[0]
assert res.ndim==2 and res.shape[1]==521
assert names[211]=="Pop music"
print("RDI_YAMNET_ARM64_SELF_TEST=SUCCESS")
PY
install -m 644 "$SRC/oracle/rdi-music-ai-analyze.service" /etc/systemd/system/rdi-music-ai-analyze.service
install -m 644 "$SRC/oracle/rdi-music-ai-analyze.timer" /etc/systemd/system/rdi-music-ai-analyze.timer
systemctl daemon-reload
systemctl enable --now rdi-music-ai-analyze.timer
systemctl is-active --quiet rdi-music-ai-analyze.timer
# Refresh the UI with zero AI results first; the background processing is separate.
runuser -u ubuntu -- env HOME=/home/ubuntu python3 "$APP/rdi_music_dj.py" report >/dev/null
systemctl restart rdi-music-dj-web.service
systemctl is-active --quiet rdi-music-dj-web.service
curl -fsS --max-time 9 http://127.0.0.1:8788/api/report |
 python3 -c 'import sys,json;d=json.load(sys.stdin); assert d["read_only"] and d["playlist_writes"] == 0 and d["ai_sample_target"]==100; print("RDI_DJ_AI_DASHBOARD=READY")'
echo "RDI_DJ_AI_MODEL=YAMNET_ONNX_APACHE_2"
echo "RDI_DJ_AI_PLAYLIST_WRITES=ZERO"
