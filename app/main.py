from typing import Annotated
from fastapi import FastAPI, Request, Depends, Body, Path
from starlette.responses import RedirectResponse
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from pydantic import BaseModel
from datetime import datetime
import os
from .dependencies import DbConnectionDep
from .routers import api
from .smb import SMB
from sqlite3 import Connection

app = FastAPI()
app.include_router(api.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

smb_server = os.environ["smb_server"]
dst_root = os.environ["dst_root"]
smb = SMB(smb_server, os.environ["smb_username"], os.environ["smb_password"])

@app.get("/", response_class=HTMLResponse)
def digestions(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        WITH agg_recs AS(
            SELECT
                program_id, json_group_array(id) AS rec_ids
                ,
                json_group_array(CASE WHEN watched_at IS NOT NULL THEN 1 ELSE 0 END) AS watcheds
            FROM recordings
            WHERE watched_at IS NULL AND deleted_at IS NULL
            GROUP BY program_id
        )
        , agg_views AS (
            SELECT program_id, json_group_array(viewed_time) AS views
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

    return templates.TemplateResponse(
        request=request, name="index.html", context={"agg": agg, "rec_zip": rec_zip})

@app.get("/programs", response_class=HTMLResponse)
def programs(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        WITH agg_views AS (
            SELECT program_id, json_group_array(viewed_time) AS views
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
    return templates.TemplateResponse(
        request=request, name="programs.html", context={"programs": programs})

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
    return templates.TemplateResponse(
        request=request, name="recordings.html", context={"recordings": recordings})

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
    return templates.TemplateResponse(
        request=request, name="views.html", context={"views": views})


class Program(BaseModel):
    event_id: int
    service_id: int
    name: str
    start_time: datetime
    duration: int

def get_or_create_program(con: Connection, program: Program, created_at: datetime, viewed_time: datetime) -> int:
    cur = con.cursor()
    cur.execute("""
        SELECT id, duration, created_at AS "created_at [timestamp]"
        FROM programs
        WHERE event_id = ? AND service_id = ? AND start_time = ?
    """, (
        program.event_id,
        program.service_id,
        program.start_time
    ))
    row = cur.fetchone()

    if row:
        id, duration, c = row
        if duration != program.duration and c < viewed_time:
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
def set_viewed_deprecated(data: ViewRequest, con: DbConnectionDep):
    program_id = get_or_create_program(con, data.program, data.viewed_time, data.viewed_time)

    cursor = con.cursor()
    cursor.execute("""
        INSERT INTO views (program_id, viewed_time, created_at)
        VALUES (?, ?, ?)
    """, (program_id, data.viewed_time, datetime.now()))
    con.commit()
    return {}

class RecordRequest(BaseModel):
    program: Program
    file_path: str
    recorded_at: datetime

@app.post("/api/recorded")
def set_recorded_deprecated(data: RecordRequest, con: DbConnectionDep):
    program_id = get_or_create_program(con, data.program, data.recorded_at, data.recorded_at)

    con.execute("""
        INSERT INTO recordings (program_id, file_path, created_at)
        VALUES (?, ?, ?)
    """, (program_id, f"//{smb_server}{data.file_path}", data.recorded_at))
    con.commit()
    return {}

class WatchRequest(BaseModel):
    recording_id: int
    move_file: bool

@app.post("/api/watched")
def set_watched_deprecated(data: WatchRequest, con: DbConnectionDep):
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
