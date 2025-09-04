#!/bin/sh
set -eux

if [ "${DB:-}" = "sqlite" ]; then
  (cat /app/db/schema.sql; echo ".quit") | python -m sqlite3 /app/db/tv.db
fi

if [ "${1:-}" = "dev" ]; then
  uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload --reload-dir app --log-level debug
elif [ "${1:-}" = "test" ]; then
  shift
  pytest ./app "$@"
else
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
fi
