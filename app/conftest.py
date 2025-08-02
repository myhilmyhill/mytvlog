import pytest
from fastapi import BackgroundTasks
from unittest.mock import Mock
from fastapi.testclient import TestClient
from .main import app
from .smb import SMB
from .edcb import CtrlCmdUtil
from .dependencies import make_db_connection, get_db_connection, get_db_connection_factory, get_smb, get_edcb, get_prog_repo, get_rec_repo, get_view_repo, get_dig_repo
from .repositories.sqlite.api import (
    SQLiteProgramRepository, SQLiteRecordingRepository, SQLiteViewRepository, SQLiteDigestionRepository
)

@pytest.fixture
def con():
    con = make_db_connection(":memory:", check_same_thread=False)

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
    app.dependency_overrides[get_prog_repo] = lambda: SQLiteProgramRepository(con)
    app.dependency_overrides[get_rec_repo] = lambda: SQLiteRecordingRepository(con)
    app.dependency_overrides[get_view_repo] = lambda: SQLiteViewRepository(con)
    app.dependency_overrides[get_dig_repo] = lambda: SQLiteDigestionRepository(con)

    # middleware はテストではすべて読み込まない
    app.user_middleware.clear()
    app.middleware_stack = app.build_middleware_stack()

    # テストでは即座に実行する
    BackgroundTasks.add_task = lambda self, func, *args, **kwargs: func(*args, **kwargs)

    client = TestClient(app)
    yield client
    app.dependency_overrides = {}
