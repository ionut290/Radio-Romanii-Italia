#!/usr/bin/env bash
set -Eeuo pipefail
export PATH=/usr/local/bin:/usr/bin:/bin
ROOT="/home/ubuntu/rdi-geopolitica"
LOCK="/tmp/rdi-geopolitica-publish.lock"
exec 9>"$LOCK"
flock -n 9 || { echo "Geopolitica: another publisher is running"; exit 0; }
cd "$ROOT"
test -f scripts/update_geopolitica.py
test -f data/geopolitica-news.json
if ! git diff --quiet -- data/geopolitica-news.json; then
  echo "STOP: pre-existing local geopolitica JSON changes; manual reconciliation required" >&2
  exit 1
fi
if ! git diff --cached --quiet; then
  echo "STOP: staged changes exist; refusing to publish" >&2
  exit 1
fi
if test -n "$(git status --porcelain --untracked-files=no | grep -v '^.. data/geopolitica-news.json$' || true)"; then
  echo "STOP: unrelated tracked changes exist" >&2
  exit 1
fi
git fetch origin main
if ! git merge-base --is-ancestor HEAD origin/main; then
  echo "STOP: local branch diverged; manual reconciliation required" >&2
  exit 1
fi
git merge --ff-only origin/main
python3 scripts/update_geopolitica.py
python3 - <<'PY'
import json
from pathlib import Path
data=json.loads(Path("data/geopolitica-news.json").read_text(encoding="utf-8"))
assert data.get("schema_version")==2
assert isinstance(data.get("items"),list) and data["items"]
assert all(x.get("title_ro") and x.get("title_it") and x.get("url","").startswith("https://") for x in data["items"])
print("Validated bilingual news:",len(data["items"]))
PY
if git diff --quiet -- data/geopolitica-news.json; then
  echo "No changes to publish"
  exit 0
fi
git config user.name "rdi-oracle-publisher"
git config user.email "rdi-oracle-publisher@users.noreply.github.com"
git add -- data/geopolitica-news.json
git commit -m "RDI: aggiornamento geopolitica da Oracle"
if ! git push origin HEAD:main; then
  echo "STOP: push failed; commit preserved locally. Reconcile before retrying." >&2
  exit 1
fi
echo "Published geopolitica news successfully"
