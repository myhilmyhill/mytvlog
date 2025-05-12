import pytest
import sqlite3
from fastapi.testclient import TestClient
from .main import app, get_db_connection

client = TestClient(app)

@pytest.fixture
def con():
    con = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_COLNAMES, check_same_thread=False)
    con.row_factory = sqlite3.Row

    with open("db/schema.sql") as f:
        con.executescript(f.read())

    yield con

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
        INSERT INTO programs (id, service_id, name, start_time, duration, created_at) VALUES
            (1, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:10:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at) VALUES
            (1, 1, '/rec1', unixepoch('2025-05-12T12:30:00+09:00'), NULL),
            (2, 1, '/rec2', NULL, NULL);
        INSERT INTO views (program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T13:00:00+09:00'));
    """)
    response = client.get("/")
    assert response.status_code == 200
