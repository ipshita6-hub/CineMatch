#!/usr/bin/env bash
# Start the FastAPI backend. Port is configurable: PORT=8011 ./scripts/run_backend.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8011}"
cd "$ROOT/backend"
PYTHONPATH="$ROOT:$ROOT/backend" exec "$ROOT/venv/bin/uvicorn" app.main:app \
  --host "${HOST:-127.0.0.1}" --port "$PORT" --log-level "${LOG_LEVEL:-info}"
