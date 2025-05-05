from fastapi import FastAPI, Request, Form
from starlette.responses import RedirectResponse
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import sqlite3
from sqlite3 import Connection

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DB_PATH = "/app/db/tv.db"
JST = timezone(timedelta(hours=9))

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, channel_name, start_time, duration, created_at FROM programs ORDER BY start_time DESC")
        programs = cur.fetchall()

        cur.execute("SELECT id, program_id, file_path, deleted_at FROM recordings")
        recordings = cur.fetchall()

        cur.execute("SELECT program_id, view_state, viewed_at FROM view_statuses")
        view_statuses = cur.fetchall()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tv": {"programs": programs, "recordings": recordings, "view_statuses": view_statuses}
    })

class Program(BaseModel):
    channel_name: str
    name: str
    start_time: datetime
    duration: int

class ViewStateUpdateByInfo(BaseModel):
    program: Program
    viewed_at: datetime

def get_or_create_program(conn: Connection, program: Program, created_at: datetime) -> int:
    cursor = conn.cursor()
    conn.execute("""
        SELECT id FROM programs
        WHERE channel_name = ? AND name = ? AND start_time = ? AND duration = ?
    """, (
        program.channel_name,
        program.name,
        program.start_time.isoformat(),
        program.duration
    ))
    row = cursor.fetchone()

    if row:
        return row["id"]

    cursor.execute("""
        INSERT INTO programs (name, channel_name, start_time, duration, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        program.name,
        program.channel_name,
        program.start_time.isoformat(),
        program.duration,
        created_at.isoformat()
    ))
    return cursor.lastrowid

@app.post("/api/watched")
def set_watched_by_info(data: ViewStateUpdateByInfo):
    conn = sqlite3.connect(DB_PATH)
    program_id = get_or_create_program(conn, data.program, data.viewed_at)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO view_statuses (program_id, view_state, viewed_at)
        VALUES (?, 'watched', ?)
        ON CONFLICT(program_id)
        DO UPDATE SET view_state='watched', viewed_at=excluded.viewed_at
    """, (program_id, data.viewed_at.isoformat()))

    conn.commit()
    conn.close()

    return {
        "message": f"Marked as watched: {data.program.name}",
        "viewed_at": data.viewed_at.isoformat()
    }

class RecordRequest(BaseModel):
    program: Program
    file_path: str
    recorded_at: datetime

@app.post("/api/recorded")
def set_recorded_by_info(data: RecordRequest):
    conn = sqlite3.connect(DB_PATH)

    program_id = get_or_create_program(conn, data.program, data.recorded_at)

    conn.execute("""
        INSERT OR IGNORE INTO recordings (program_id, file_path)
        VALUES (?, ?)
    """, (program_id, data.file_path))

    conn.commit()
    return {"program_id": program_id, "recorded_at": data.recorded_at}
