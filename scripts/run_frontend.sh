#!/usr/bin/env bash
# Start the Vite dev server.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"
exec npx vite --port "${PORT:-5173}"
