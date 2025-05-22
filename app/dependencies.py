from typing import Annotated, Callable
from fastapi import Depends, BackgroundTasks
from pydantic import AfterValidator
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import os
import sqlite3
from .smb import SMB
from .edcb import CtrlCmdUtil

JST = ZoneInfo("Asia/Tokyo")

def localize_to_jst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=JST)
    return dt.astimezone(JST)

JSTDatetime = Annotated[datetime, AfterValidator(localize_to_jst)]

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

    return con

DB_PATH = "db/tv.db"

def get_db_connection():
    con = make_db_connection(DB_PATH)
    try:
        yield con
    finally:
        con.close()

DbConnectionDep = Annotated[sqlite3.Connection, Depends(get_db_connection)]

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
