import pytest
import sqlite3
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from fastapi.testclient import TestClient
from .main import app
from .smb import SMB
from .dependencies import get_db_connection, get_smb

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
def smb():
    yield Mock(spec=SMB)

@pytest.fixture
def client(con, smb):
    def override_get_db():
        try:
            yield con
        finally:
            pass

    def override_get_smb():
        try:
            yield smb
        finally:
            pass

    app.dependency_overrides[get_db_connection] = override_get_db
    app.dependency_overrides[get_smb] = override_get_smb
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

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
