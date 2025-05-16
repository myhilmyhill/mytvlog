from typing import Annotated
from fastapi import Depends
from datetime import datetime, timezone, timedelta
import os
import sqlite3
from .smb import SMB

def get_db_connection():
    DB_PATH = "db/tv.db"
    con = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_COLNAMES)
    con.row_factory = sqlite3.Row

    def adapt_datetime_epoch(val):
        """Adapt datetime.datetime to Unix timestamp."""
        return int(val.timestamp())

    sqlite3.register_adapter(datetime, adapt_datetime_epoch)

    def convert_timestamp(val):
        """Convert Unix epoch timestamp to datetime.datetime object."""
        return datetime.fromtimestamp(int(val)).astimezone(timezone(timedelta(hours=9)))

    sqlite3.register_converter("timestamp", convert_timestamp)

    try:
        yield con
    finally:
        con.close()

DbConnectionDep = Annotated[sqlite3.Connection, Depends(get_db_connection)]

def get_smb():
    smb_server = os.environ["smb_server"]
    yield SMB(smb_server, os.environ["smb_username"], os.environ["smb_password"])

SmbDep = Annotated[SMB, Depends(get_smb)]
