#!/bin/bash
set -euo pipefail

# 必要な環境変数
SQLITE_DB="${sqlite_db:?環境変数 sqlite_db を設定してください}"
PROJECT="${bigquery_project_id:?環境変数 bigquery_project_id を設定してください}"
DATASET="${bigquery_dataset_id:?環境変数 bigquery_dataset_id を設定してください}"

# SQLite → JSONL エクスポート関数
export_table_programs() {
  echo "📤 Exporting programs to JSONL..."
  sqlite3 -json "$SQLITE_DB" "
    SELECT
      id,
      event_id,
      service_id,
      name,
      datetime(start_time, 'unixepoch') AS start_time,
      duration,
      text,
      ext_text,
      datetime(created_at, 'unixepoch') AS created_at
    FROM programs;" | jq -c '.[]' > programs.jsonl
}

export_table_recordings() {
  echo "📤 Exporting recordings to JSONL..."
  sqlite3 -json "$SQLITE_DB" "
    SELECT
      id,
      program_id,
      file_path,
      file_size,
      CASE WHEN watched_at IS NOT NULL THEN datetime(watched_at, 'unixepoch') END AS watched_at,
      CASE WHEN deleted_at IS NOT NULL THEN datetime(deleted_at, 'unixepoch') END AS deleted_at,
      datetime(created_at, 'unixepoch') AS created_at
    FROM recordings;" | jq -c '.[]' > recordings.jsonl
}

export_table_views() {
  echo "📤 Exporting views to JSONL..."
  sqlite3 -json "$SQLITE_DB" "
    SELECT
      program_id,
      datetime(viewed_time, 'unixepoch') AS viewed_time,
      datetime(created_at, 'unixepoch') AS created_at
    FROM views;" | jq -c '.[]' > views.jsonl
}

# BigQuery に JSONL をロード
load_to_bq() {
  local table=$1
  local file="${table}.jsonl"
  if [ -f "$file" ]; then
    echo "📥 Loading $file → BigQuery: $DATASET.$table..."
    bq load \
      --source_format=NEWLINE_DELIMITED_JSON \
      --replace \
      --project_id="$PROJECT" \
      "$DATASET.$table" \
      "$file"
  fi
}

# 実行
export_table_programs
export_table_recordings
export_table_views

load_to_bq programs
load_to_bq recordings
load_to_bq views

echo "✅ 完了：SQLite → BigQuery インポート成功（JSONL形式）"
