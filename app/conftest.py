import pytest
import sqlite3
from fastapi import BackgroundTasks
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from fastapi.testclient import TestClient
from .main import app
from .smb import SMB
from .edcb import CtrlCmdUtil
from .dependencies import get_db_connection, get_db_connection_factory, get_smb, get_edcb

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
def con_factory(con):
    def factory():
        return con
    return factory

@pytest.fixture
def smb():
    yield Mock(spec=SMB)

@pytest.fixture
def edcb():
    yield Mock(spec=CtrlCmdUtil)

@pytest.fixture
def client(con, con_factory, smb, edcb):
    def override_get_db():
        try:
            yield con
        finally:
            pass

    def override_get_db_connection_factory():
        try:
            yield con_factory
        finally:
            pass

    def override_get_smb():
        try:
            yield smb
        finally:
            pass

    def override_get_edcb():
        yield edcb

    app.dependency_overrides[get_db_connection] = override_get_db
    app.dependency_overrides[get_db_connection_factory] = override_get_db_connection_factory
    app.dependency_overrides[get_smb] = override_get_smb
    app.dependency_overrides[get_edcb] = override_get_edcb

    # テストでは即座に実行する
    BackgroundTasks.add_task = lambda self, func, *args, **kwargs: func(*args, **kwargs)

    client = TestClient(app)
    yield client
    app.dependency_overrides = {}
