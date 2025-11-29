import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from .main import app

from .dependencies import make_db_connection, get_db_connection, get_db_connection_factory, get_prog_repo, get_rec_repo, get_view_repo, get_dig_repo, get_series_repo
from .repositories.sqlite.api import (
    SQLiteProgramRepository, SQLiteRecordingRepository, SQLiteViewRepository, SQLiteDigestionRepository,
    SQLiteSeriesRepository
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
def client(con, con_factory):
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


    app.dependency_overrides[get_db_connection] = override_get_db
    app.dependency_overrides[get_db_connection_factory] = override_get_db_connection_factory
    app.dependency_overrides[get_prog_repo] = lambda: SQLiteProgramRepository(con)
    app.dependency_overrides[get_rec_repo] = lambda: SQLiteRecordingRepository(con)
    app.dependency_overrides[get_view_repo] = lambda: SQLiteViewRepository(con)
    app.dependency_overrides[get_dig_repo] = lambda: SQLiteDigestionRepository(con)
    app.dependency_overrides[get_series_repo] = lambda: SQLiteSeriesRepository(con)

    # middleware はテストではすべて読み込まない
    app.user_middleware.clear()
    app.middleware_stack = app.build_middleware_stack()

    client = TestClient(app)
    yield client
    app.dependency_overrides = {}
