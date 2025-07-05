#!/bin/sh
set -eux

(cat /app/db/schema.sql; echo ".quit") | python -m sqlite3 /app/db/tv.db
if [ "${1:-}" = "dev" ]; then
  uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload --reload-dir app --log-level debug
else
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
fi
