#!/usr/bin/env bash
# Create .venv with Python 3.11 when available; otherwise python3 (see README).
set -euo pipefail
cd "$(dirname "$0")"
if command -v python3.11 >/dev/null 2>&1; then
  PY=python3.11
else
  PY=python3
  echo "Note: python3.11 not on PATH; using ${PY} for .venv (3.11+ optional)." >&2
fi
"${PY}" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip -q
pip install -r requirements.txt
echo "Ready. Activate: source .venv/bin/activate"
