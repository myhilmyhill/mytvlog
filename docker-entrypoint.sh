#!/bin/sh
set -eu

(cat /app/db/schema.sql; echo ".quit") | python -m sqlite3 /app/db/tv.db
uvicorn app.main:app --host 0.0.0.0 --port $PORT
