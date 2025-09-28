#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/.venv/bin/python"

if [[ -x "$VENV_PY" ]]; then
    PYTHON_CMD="$VENV_PY"
else
    PYTHON_CMD="python3"
fi

exec "$PYTHON_CMD" -m musicplayer "$@"
