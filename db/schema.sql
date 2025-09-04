-- 番組情報
CREATE TABLE IF NOT EXISTS "programs"(
    id INTEGER PRIMARY KEY
  , event_id INTEGER NOT NULL
  , service_id INTEGER NOT NULL
  , name TEXT NOT NULL
  , start_time INTEGER NOT NULL
  , duration INTEGER NOT NULL
  , text TEXT
  , ext_text TEXT
  , created_at INTEGER NOT NULL
) STRICT
;
-- 録画履歴
CREATE TABLE IF NOT EXISTS "recordings"(
    id INTEGER PRIMARY KEY
  , program_id INTEGER NOT NULL
  , file_path TEXT NOT NULL
  , file_size INTEGER
  , watched_at INTEGER
  , deleted_at INTEGER
  , created_at INTEGER NOT NULL
  , FOREIGN KEY (program_id) REFERENCES programs(id)
) STRICT
;
-- 視聴状態
CREATE TABLE IF NOT EXISTS "views"(
    program_id INTEGER NOT NULL
  , viewed_time INTEGER NOT NULL
  , created_at INTEGER NOT NULL
  , FOREIGN KEY (program_id) REFERENCES programs(id)
) STRICT
;
-- 連続番組
CREATE TABLE IF NOT EXISTS "series"(
    id INTEGER PRIMARY KEY
  , name TEXT NOT NULL
  , created_at INTEGER NOT NULL
) STRICT
;
-- 番組とシリーズの多対多リレーション
CREATE TABLE IF NOT EXISTS "program_series"(
    program_id INTEGER NOT NULL
  , series_id  INTEGER NOT NULL
  , PRIMARY KEY (program_id, series_id)
  , FOREIGN KEY (program_id) REFERENCES programs(id)
  , FOREIGN KEY (series_id)  REFERENCES series(id)
) STRICT
;
