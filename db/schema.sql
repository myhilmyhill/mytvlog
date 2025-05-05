-- 番組情報
CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY,
    channel_name TEXT NOT NULL,
    name TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    duration INTEGER NOT NULL,
    [text] TEXT,
    ext_text TEXT,
    created_at DATETIME NOT NULL
);

-- 録画履歴
CREATE TABLE IF NOT EXISTS recordings (
    id INTEGER PRIMARY KEY,
    program_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    deleted_at DATETIME,
    FOREIGN KEY (program_id) REFERENCES programs(id)
);

-- 視聴状態
CREATE TABLE IF NOT EXISTS view_statuses (
    program_id INTEGER PRIMARY KEY,
    view_state TEXT NOT NULL CHECK (view_state IN ('unwatched', 'partial', 'watched')),
    viewed_at DATETIME,
    FOREIGN KEY (program_id) REFERENCES programs(id)
);
