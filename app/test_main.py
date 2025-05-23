import pytest
from .conftest import con, smb, edcb

def test_digestions(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'), NULL, 0),
            (2, 1, '//recorded/test2', NULL, NULL, 0);
        INSERT INTO views (program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T13:00:00+09:00'));
    """)
    response = client.get("/")
    assert response.status_code == 200

def test_recordings(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'), NULL, 0),
            (2, 1, '//recorded/test2', NULL, NULL, 0);
        INSERT INTO views (program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T13:00:00+09:00'));
    """)
    response = client.get("/recordings")
    assert response.status_code == 200

def test_recordings(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'), NULL, 0),
            (2, 1, '//recorded/test2', NULL, NULL, 0);
        INSERT INTO views (program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T13:00:00+09:00'));
    """)
    response = client.get("/views")
    assert response.status_code == 200
