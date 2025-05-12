#!/bin/sh
set -eu

python -m sqlite3 /app/db/tv.db < /app/db/schema.sql
uvicorn app.main:app --host 0.0.0.0 --port 80
