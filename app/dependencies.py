from typing import Annotated, Callable
from fastapi import Depends
from datetime import datetime
import os
import re
import sqlite3

from .models.api import JST
from .repositories.interfaces import DigestionRepository, ProgramRepository, RecordingRepository, ViewRepository
from .repositories.sqlite.api import SQLiteDigestionRepository, SQLiteProgramRepository, SQLiteRecordingRepository, SQLiteViewRepository
from .repositories.bigquery.api import BigQueryDigestionRepository, BigQueryProgramRepository, BigQueryRecordingRepository, BigQueryViewRepository
from .smb import SMB
from .edcb import CtrlCmdUtil

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

def get_db_connection():
    con = make_db_connection(DB_PATH)
    try:
        yield con
    finally:
        con.close()

DbConnectionDep = Annotated[sqlite3.Connection, Depends(get_db_connection)]

def get_prog_repo(con: DbConnectionDep) -> ProgramRepository:
    if os.environ["DB"] == "sqlite":
        return SQLiteProgramRepository(con)
    elif os.environ["DB"] == "bigquery":
        return BigQueryProgramRepository(BIGQUERY_PROJECT_ID, BIGQUERY_DATASET_ID)

ProgramRepositoryDep = Annotated[ProgramRepository, Depends(get_prog_repo)]

def get_rec_repo(con: DbConnectionDep) -> RecordingRepository:
    if os.environ["DB"] == "sqlite":
        return SQLiteRecordingRepository(con)
    elif os.environ["DB"] == "bigquery":
        return BigQueryRecordingRepository(BIGQUERY_PROJECT_ID, BIGQUERY_DATASET_ID)

RecordingRepositoryDep = Annotated[RecordingRepository, Depends(get_rec_repo)]

def get_view_repo(con: DbConnectionDep) -> ViewRepository:
    if os.environ["DB"] == "sqlite":
        return SQLiteViewRepository(con)
    elif os.environ["DB"] == "bigquery":
        return BigQueryViewRepository(BIGQUERY_PROJECT_ID, BIGQUERY_DATASET_ID)

ViewRepositoryDep = Annotated[ViewRepository, Depends(get_view_repo)]

def get_dig_repo(con: DbConnectionDep) -> DigestionRepository:
    if os.environ["DB"] == "sqlite":
        return SQLiteDigestionRepository(con)
    elif os.environ["DB"] == "bigquery":
        return BigQueryDigestionRepository(BIGQUERY_PROJECT_ID, BIGQUERY_DATASET_ID)

DigestionRepositoryDep = Annotated[DigestionRepository, Depends(get_dig_repo)]

def get_db_connection_factory():
    """BackgroundTasks など別スレッドで接続する用
       使い終わったら close する必要あり
    """
    return lambda: make_db_connection(DB_PATH)

DbConnectionFactoryDep = Annotated[Callable[[], sqlite3.Connection], Depends(get_db_connection_factory)]

def get_smb():
    smb_server = os.environ["smb_server"]
    yield SMB(smb_server, os.environ["smb_username"], os.environ["smb_password"])

SmbDep = Annotated[SMB, Depends(get_smb)]

def get_edcb():
    server = os.environ["edcb_server"]
    port = os.getenv("edcb_port", "4510")
    c = CtrlCmdUtil()
    c.setNWSetting(server, port)
    yield c

EdcbDep = Annotated[CtrlCmdUtil, Depends(get_edcb)]
