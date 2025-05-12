import pytest
import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from .main import app, get_db_connection

@pytest.fixture
def con():
    con = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_COLNAMES, check_same_thread=False)
    con.row_factory = sqlite3.Row

    def adapt_datetime_epoch(val):
        """Adapt datetime.datetime to Unix timestamp."""
        return int(val.timestamp())

    sqlite3.register_adapter(datetime, adapt_datetime_epoch)

    def convert_timestamp(val):
        """Convert Unix epoch timestamp to datetime.datetime object."""
        return datetime.fromtimestamp(int(val)).astimezone(timezone(timedelta(hours=9)))

    sqlite3.register_converter("timestamp", convert_timestamp)

    with open("db/schema.sql") as f:
        con.executescript(f.read())

    yield con
    con.close()

@pytest.fixture
def client(con):
    def override_get_db():
        try:
            yield con
        finally:
            pass

    app.dependency_overrides[get_db_connection] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_digestions(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at) VALUES
            (1, 1, '/test1', unixepoch('2025-05-12T12:30:00+09:00'), NULL),
            (2, 1, '/test2', NULL, NULL);
        INSERT INTO views (program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T13:00:00+09:00'));
    """)
    response = client.get("/")
    assert response.status_code == 200

def test_get_program(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.get("/api/programs/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_set_viewed(con, client):
    response = client.post("/api/viewed", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:05:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["event_id"] == 11

def test_set_viewed_延長でdurationが延びる(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.post("/api/viewed", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1860,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:05:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["duration"] == 1860

def test_set_viewed_延長でdurationが縮む(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.post("/api/viewed", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1740,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:05:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["duration"] == 1740

def test_set_viewed_created_atより前のviewed_timeでdurationが変化しても古い値で上書きしない(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.post("/api/viewed", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1860,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:00:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["duration"] == 1800

def test_get_recorded(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at) VALUES
            (1, 1, '/test1', unixepoch('2025-05-12T12:30:00+09:00'), NULL);
    """)
    response = client.get("/api/recordings/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_set_recorded(con, client):
    response = client.post("/api/recorded", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "file_path": "/test1",
        "recorded_at": "2025-05-12T12:30:00+09:00",
    })
    assert response.status_code == 200

def test_set_watched(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:10:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at) VALUES
            (1, 1, '/test1', NULL, NULL);
    """)

    response = client.post("/api/watched", json={
        "recording_id": 1,
        "move_file": False,
        "watched_at": "2025-05-12T12:30:00+09:00",
    })
    assert response.status_code == 200
    recording = client.get("/api/recordings/1").json()
    # assert recording["watched_at"] == "2025-05-12T12:30:00+09:00"
