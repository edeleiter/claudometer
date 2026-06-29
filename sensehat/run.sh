#!/usr/bin/env bash
# Launch the Claudometer Sense HAT display.
# Used both for manual runs and by the systemd service.
#
# Any arguments are forwarded to the app, e.g.:
#   ./sensehat/run.sh --demo --backend stub
#   ./sensehat/run.sh --rotation 180
set -euo pipefail

# Repo root = parent of this script's directory, regardless of where it's called from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Launch order:
# 1. A project venv at .venv (the reliable path for the systemd service). On the
#    Pi, create it so apt's sense_hat stays visible:
#        uv venv --system-site-packages && uv pip install requests
# 2. Otherwise, if uv is installed, run in an ephemeral env (handy for desktop
#    --demo / --emulator runs). Add a sense backend with --with as needed.
# 3. Fall back to system python3.
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  exec "$REPO_ROOT/.venv/bin/python" -m sensehat.app "$@"
elif command -v uv >/dev/null 2>&1; then
  exec uv run --no-project --with requests python -m sensehat.app "$@"
else
  exec "$(command -v python3 || command -v python)" -m sensehat.app "$@"
fi
