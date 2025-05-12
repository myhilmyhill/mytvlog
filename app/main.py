from typing import Annotated
from fastapi import FastAPI, Request, Depends
from starlette.responses import RedirectResponse
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import sqlite3
from sqlite3 import Connection
import os
from .smb import SMB

jst = timezone(timedelta(hours=9))
app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def get_db_connection():
    DB_PATH = "db/tv.db"
    con = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_COLNAMES)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()
DbConnectionDep = Annotated[sqlite3.Connection, Depends(get_db_connection)]

def adapt_datetime_epoch(val):
    """Adapt datetime.datetime to Unix timestamp."""
    return int(val.timestamp())

sqlite3.register_adapter(datetime, adapt_datetime_epoch)

def convert_timestamp(val):
    """Convert Unix epoch timestamp to datetime.datetime object."""
    return datetime.fromtimestamp(int(val)).astimezone(jst)

sqlite3.register_converter("timestamp", convert_timestamp)

smb_server = os.environ["smb_server"]
dst_root = os.environ["dst_root"]
smb = SMB(smb_server, os.environ["smb_username"], os.environ["smb_password"])

@app.get("/", response_class=HTMLResponse)
def digestions(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        WITH agg_recs AS(
            SELECT
                program_id, group_concat(id, ',') AS rec_ids
                ,
                group_concat(CASE WHEN watched_at IS NOT NULL THEN 1 ELSE 0 END, ',') AS watcheds
            FROM recordings
            WHERE watched_at IS NULL AND deleted_at IS NULL
            GROUP BY program_id
        )
        , agg_views AS (
            SELECT program_id, group_concat(viewed_time, ',') AS views
            FROM views
            GROUP BY program_id
        )
        SELECT
            programs.id, programs.name, programs.service_id, programs.start_time, programs.duration
            ,
            programs.start_time AS "start_time_string [timestamp]"
            ,
            agg_views.views
            ,
            agg_recs.rec_ids, agg_recs.watcheds
        FROM programs
        INNER JOIN agg_recs ON agg_recs.program_id = programs.id
        LEFT OUTER JOIN agg_views ON agg_views.program_id = programs.id
        ORDER BY programs.start_time
    """)
    agg = cur.fetchall()
    rec_zip = lambda id: zip(*next([x["rec_ids"].split(","), x["watcheds"].split(",")] for x in agg if x["id"] == id))

    return templates.TemplateResponse("index.html", {
        "request": request,
        "agg": agg, "rec_zip": rec_zip
    })

@app.get("/programs", response_class=HTMLResponse)
def programs(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        WITH agg_views AS (
            SELECT program_id, group_concat(viewed_time, ',') AS views
            FROM views
            GROUP BY program_id
        )
        SELECT id, name, service_id, start_time
            ,
            start_time AS "start_time_str [timestamp]",
            start_time + duration AS "end_time_str [timestamp]",
            duration,
            created_at AS "created_at [timestamp]"
            ,
            agg_views.views
        FROM programs
        LEFT OUTER JOIN agg_views ON agg_views.program_id = programs.id
        ORDER BY start_time DESC
    """)
    programs = cur.fetchall()
    return templates.TemplateResponse("programs.html", {
        "request": request,
        "programs": programs
    })

@app.get("/recordings", response_class=HTMLResponse)
def recordings(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        SELECT recordings.id, program_id, file_path,
            watched_at AS "watched_at [timestamp]", deleted_at AS "deleted_at [timestamp]",
            programs.name, programs.service_id
        FROM recordings
        INNER JOIN programs ON programs.id = recordings.program_id
        ORDER BY programs.start_time DESC
    """)
    recordings = cur.fetchall()
    return templates.TemplateResponse("recordings.html", {
        "request": request,
        "recordings": recordings
    })

@app.get("/views", response_class=HTMLResponse)
def views(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        SELECT program_id, viewed_time AS "viewed_time [timestamp]", programs.name,
            views.created_at AS "created_at [timestamp]"
        FROM views
        INNER JOIN programs ON programs.id = views.program_id
        ORDER BY "created_at [timestamp]" DESC
    """)
    views = cur.fetchall()
    return templates.TemplateResponse("views.html", {
        "request": request,
        "views": views
    })


class Program(BaseModel):
    event_id: int
    service_id: int
    name: str
    start_time: datetime
    duration: int

@app.get("/api/programs/{id}")
def get_program(id: int, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("SELECT * FROM programs WHERE id = :id", (id,))
    item = cur.fetchone()
    return item

def get_or_create_program(con: Connection, program: Program, created_at: datetime) -> int:
    cur = con.cursor()
    cur.execute("""
        SELECT id, duration
        FROM programs
        WHERE event_id = ? AND service_id = ? AND start_time = ?
    """, (
        program.event_id,
        program.service_id,
        program.start_time
    ))
    row = cur.fetchone()

    if row:
        id, duration = row
        if duration > program.duration:
            cur.execute("UPDATE programs SET duration = ? WHERE id = ?", (program.duration, id))
        return id

    cur.execute("""
        INSERT INTO programs (event_id, service_id, name, start_time, duration, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        program.event_id,
        program.service_id,
        program.name,
        program.start_time,
        program.duration,
        created_at
    ))
    return cur.lastrowid

class ViewRequest(BaseModel):
    program: Program
    viewed_time: datetime

@app.post("/api/viewed")
def set_viewed(data: ViewRequest, con: DbConnectionDep):
    program_id = get_or_create_program(con, data.program, data.viewed_time)

    cursor = con.cursor()
    cursor.execute("""
        INSERT INTO views (program_id, viewed_time, created_at)
        VALUES (?, ?, ?)
    """, (program_id, data.viewed_time, datetime.now()))
    con.commit()
    return {}

@app.get("/api/recordings/{id}")
def get_recorded(id: int, con: DbConnectionDep):
    cur = con.execute("SELECT * FROM recordings WHERE ID = ?", (id,))
    item = cur.fetchone()
    return item

class RecordRequest(BaseModel):
    program: Program
    file_path: str
    recorded_at: datetime

@app.post("/api/recorded")
def set_recorded(data: RecordRequest, con: DbConnectionDep):
    program_id = get_or_create_program(con, data.program, data.recorded_at)

    con.execute("""
        INSERT INTO recordings (program_id, file_path)
        VALUES (?, ?)
    """, (program_id, f"//{smb_server}{data.file_path}"))
    con.commit()
    return {}

class WatchRequest(BaseModel):
    recording_id: int
    move_file: bool

@app.post("/api/watched")
def set_watched(data: WatchRequest, con: DbConnectionDep):
    if data.move_file:
        cur = con.execute("SELECT file_path FROM recordings WHERE id = ?", (data.recording_id,))
        file_path, = cur.fetchone()
        dst_file_path = smb.move_folder_by_root(file_path, dst_root)
        con.execute("""
            UPDATE recordings SET watched_at = ?, file_path = ? WHERE id = ?
        """, (datetime.now(), dst_file_path, data.recording_id))
    else:
        con.execute("""
            UPDATE recordings SET watched_at = ? WHERE id = ?
        """, (datetime.now(), data.recording_id))

    con.commit()
    return {}

class DeleteRequest(BaseModel):
    recording_id: int
    delete_file: bool

@app.post("/api/deleted")
def set_deleted(data: DeleteRequest, con: DbConnectionDep):
    con.execute("""
        UPDATE recordings SET deleted_at = ? WHERE id = ?
    """, (datetime.now(), data.recording_id))

    con.commit()
    return {}
