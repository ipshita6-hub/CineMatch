#!/usr/bin/env bash
# Create the databases, apply migrations, and seed the movie catalog.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for db in movierec movierec_test; do
  if psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$db'" | grep -q 1; then
    echo "database $db already exists"
  else
    createdb "$db" && echo "created database $db"
  fi
done

cd "$ROOT/backend"
PYTHONPATH="$ROOT" "$ROOT/venv/bin/alembic" upgrade head
cd "$ROOT"
"$ROOT/venv/bin/python" scripts/seed_movies.py
echo "Database ready."
