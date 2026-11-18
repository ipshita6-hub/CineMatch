#!/usr/bin/env bash
# Run every test suite: ML, backend, frontend.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== ML tests =="
cd "$ROOT" && PYTHONPATH="$ROOT" "$ROOT/venv/bin/pytest" ml/tests -q

echo "== Backend tests =="
cd "$ROOT/backend" && PYTHONPATH="$ROOT:$ROOT/backend" "$ROOT/venv/bin/pytest" tests -q

echo "== Frontend tests =="
cd "$ROOT/frontend" && npx vitest run
