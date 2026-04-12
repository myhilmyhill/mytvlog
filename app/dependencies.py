from typing import Annotated, Callable
from fastapi import Depends
from datetime import datetime
import os
import re
import sqlite3

from .models.api import JST
from .repositories.interfaces import DigestionRepository, ProgramRepository, RecordingRepository, SeriesRepository, ViewRepository

def make_db_connection(db_path, **kwargs):
    con = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_COLNAMES, **kwargs)
    con.row_factory = sqlite3.Row

    def adapt_datetime_epoch(val):
        """Adapt datetime.datetime to Unix timestamp."""
        return int(val.timestamp())

    sqlite3.register_adapter(datetime, adapt_datetime_epoch)

    def convert_timestamp(val):
        """Convert Unix epoch timestamp to datetime.datetime object."""
        return datetime.fromtimestamp(int(val)).astimezone(JST)

    sqlite3.register_converter("timestamp", convert_timestamp)

    def regexp(pattern, value):
        if value is None:
            return False
        return re.search(pattern, value) is not None

    con.create_function("regexp", 2, regexp)

    return con

DB_PATH = "db/tv.db"
BIGQUERY_PROJECT_ID = os.getenv("bigquery_project_id")
BIGQUERY_DATASET_ID = os.getenv("bigquery_dataset_id")

def get_db():
    db_type = os.getenv("DB")
    if db_type == "sqlite":
        con = make_db_connection(DB_PATH)
        try:
            yield con
        finally:
            con.close()
    else:
        yield None

DbDep = Annotated[sqlite3.Connection | None, Depends(get_db)]

_bigquery_client = None

def get_bigquery_client():
    global _bigquery_client
    if _bigquery_client is None:
        from google.cloud import bigquery
        _bigquery_client = bigquery.Client(
            project=BIGQUERY_PROJECT_ID,
            client_options={"api_endpoint": "https://bigquery.googleapis.com"}
        )
    return _bigquery_client

def get_prog_repo(db: DbDep):
    db_type = os.getenv("DB")
    if db_type == "sqlite":
        from .repositories.sqlite.api import SQLiteProgramRepository
        return SQLiteProgramRepository(db)
    elif db_type == "bigquery":
        from .repositories.bigquery.api import BigQueryProgramRepository
        return BigQueryProgramRepository(get_bigquery_client(), BIGQUERY_DATASET_ID)
    raise RuntimeError(f"Unsupported DB type: {db_type}")

ProgramRepositoryDep = Annotated[ProgramRepository, Depends(get_prog_repo)]

def get_rec_repo(db: DbDep):
    db_type = os.getenv("DB")
    if db_type == "sqlite":
        from .repositories.sqlite.api import SQLiteRecordingRepository
        return SQLiteRecordingRepository(db)
    elif db_type == "bigquery":
        from .repositories.bigquery.api import BigQueryRecordingRepository
        return BigQueryRecordingRepository(get_bigquery_client(), BIGQUERY_DATASET_ID)
    raise RuntimeError(f"Unsupported DB type: {db_type}")

RecordingRepositoryDep = Annotated[RecordingRepository, Depends(get_rec_repo)]

def get_view_repo(db: DbDep):
    db_type = os.getenv("DB")
    if db_type == "sqlite":
        from .repositories.sqlite.api import SQLiteViewRepository
        return SQLiteViewRepository(db)
    elif db_type == "bigquery":
        from .repositories.bigquery.api import BigQueryViewRepository
        return BigQueryViewRepository(get_bigquery_client(), BIGQUERY_DATASET_ID)
    raise RuntimeError(f"Unsupported DB type: {db_type}")

ViewRepositoryDep = Annotated[ViewRepository, Depends(get_view_repo)]

def get_dig_repo(db: DbDep):
    db_type = os.getenv("DB")
    if db_type == "sqlite":
        from .repositories.sqlite.api import SQLiteDigestionRepository
        return SQLiteDigestionRepository(db)
    elif db_type == "bigquery":
        from .repositories.bigquery.api import BigQueryDigestionRepository
        return BigQueryDigestionRepository(get_bigquery_client(), BIGQUERY_DATASET_ID)
    raise RuntimeError(f"Unsupported DB type: {db_type}")

DigestionRepositoryDep = Annotated[DigestionRepository, Depends(get_dig_repo)]

def get_series_repo(db: DbDep):
    db_type = os.getenv("DB")
    if db_type == "sqlite":
        from .repositories.sqlite.api import SQLiteSeriesRepository
        return SQLiteSeriesRepository(db)
    elif db_type == "bigquery":
        from .repositories.bigquery.api import BigQuerySeriesRepository
        return BigQuerySeriesRepository(get_bigquery_client(), BIGQUERY_DATASET_ID)
    raise RuntimeError(f"Unsupported DB type: {db_type}")

SeriesRepositoryDep = Annotated[SeriesRepository, Depends(get_series_repo)]

def get_db_connection_factory():
    """BackgroundTasks など別スレッドで接続する用
       使い終わったら close する必要あり
    """
    return lambda: make_db_connection(DB_PATH)

DbConnectionFactoryDep = Annotated[Callable[[], sqlite3.Connection], Depends(get_db_connection_factory)]
