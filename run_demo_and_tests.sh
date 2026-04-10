#!/usr/bin/env bash
# One-shot: ensure venv, demo, then pytest. Safe to paste nothing — just run this file.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ ! -x setup.sh ]]; then chmod +x setup.sh; fi
if [[ ! -d .venv ]]; then
  ./setup.sh
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m app.main demo
pytest tests/ -v
