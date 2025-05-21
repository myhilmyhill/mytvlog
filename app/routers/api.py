from typing import Annotated
from fastapi import APIRouter, Depends, Body, Path, HTTPException, BackgroundTasks, Response, status

from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from sqlite3 import Connection
from ..smb import SMB
from ..dependencies import DbConnectionDep, DbConnectionFactoryDep, SmbDep
from .recordings import file_paths, import_api

router = APIRouter()
router.include_router(file_paths.router)
router.include_router(import_api.router)

def extract_model_fields(model: type[BaseModel], row: dict, aliases: dict[str, str] = None) -> dict:
    aliases = aliases or {}
    result = {}
    keys = row.keys()
    for field_name in model.model_fields.keys():
        source_key = aliases.get(field_name, field_name)
        if source_key in keys:
            result[field_name] = row[source_key]
    return result

class Program(BaseModel):
    event_id: int
    service_id: int
    name: str
    start_time: datetime
    duration: int
    text: str | None = None
    ext_text: str | None = None
    created_at: datetime | None = None

class ProgramGet(Program):
    id: int
    end_time: datetime
    created_at: datetime

@router.get("/api/programs/{id}")
def get_program(id: int, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        SELECT
            id, event_id, service_id, name, start_time AS "start_time [timestamp]"
            ,
            duration, text, ext_text, created_at AS "created_at [timestamp]"
        FROM programs WHERE id = ?
    """, (id,))
    item = cur.fetchone()
    if item is None:
        raise HTTPException(status_code=404)

    return ProgramGet(**item, end_time=item["start_time"] + timedelta(seconds=item["duration"]))

@router.post("/api/programs")
@router.patch("/api/programs/{id}")
def create_program():
    raise NotImplementedError

def get_or_create_program(con: Connection, program: Program, created_at: datetime, viewed_time: datetime) -> int:
    cur = con.cursor()
    cur.execute("""
        SELECT id, duration, created_at AS "created_at [timestamp]"
        FROM programs
        WHERE event_id = ? AND service_id = ? AND start_time = ?
    """, (
        program.event_id,
        program.service_id,
        program.start_time,
    ))
    row = cur.fetchone()

    if row:
        id, duration, c = row
        if duration != program.duration and c < viewed_time:
            cur.execute("UPDATE programs SET duration = ? WHERE id = ?", (program.duration, id))
        return id

    cur.execute("""
        INSERT INTO programs (event_id, service_id, name, start_time, duration, text, ext_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        program.event_id,
        program.service_id,
        program.name,
        program.start_time,
        program.duration,
        program.text,
        program.ext_text,
        created_at
    ))
    return cur.lastrowid

class ViewBase(BaseModel):
    program: Program
    viewed_time: datetime
    created_at: datetime

class ViewIn(ViewBase):
    created_at: datetime = datetime.now()

@router.post("/api/viewes")
def set_view(item: ViewIn, con: DbConnectionDep):
    program_id = get_or_create_program(con, item.program, item.viewed_time, item.viewed_time)

    cursor = con.cursor()
    cursor.execute("""
        INSERT INTO views (program_id, viewed_time, created_at)
        VALUES (?, ?, ?)
    """, (program_id, item.viewed_time, datetime.now()))
    con.commit()
    return {}

class Recording(BaseModel):
    program: Program
    file_path: str
    watched_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime

class RecordingGet(Recording):
    id: int
    file_folder: str | None

class RecordingPost(Recording):
    file_folder: str | None = None
    watched_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime = datetime.now()

class RecordingPatch(BaseModel):
    file_path: str | None = Field(
        default=None,
        title="変更しても、実際のファイルの場所は移動されません。file_folder, deleted_at と同時に設定できません",
    )
    file_folder: str | None = Field(
        default=None, title="変更した場合、実際のファイルの場所も移動されます"
    )
    watched_at: datetime | None = None
    deleted_at: datetime | None = Field(
        default=None, title="値を設定した場合、実際のファイルも削除されます"
    )

@router.get("/api/recordings/{id}", response_model=RecordingGet)
def get_recording(id: int, con: DbConnectionDep):
    cur = con.execute("""
        SELECT
            recordings.id, recordings.program_id, recordings.file_path, recordings.watched_at AS "watched_at [timestamp]", recordings.deleted_at AS "deleted_at [timestamp]", recordings.created_at AS "created_at [timestamp]"
            ,
            programs.event_id, programs.service_id, programs.name, programs.start_time AS "start_time [timestamp]", programs.duration, programs.text, programs.ext_text, programs.created_at AS "program_created_at [timestamp]"
        FROM recordings INNER JOIN programs ON programs.id = recordings.program_id
        WHERE recordings.id = ?
    """, (id,))
    row = cur.fetchone()
    if row is None:
        return HTTPException(status_code=404)

    return RecordingGet(**extract_model_fields(RecordingGet, row),
        program = Program(**extract_model_fields(Program, row, aliases={"created_at": "program_created_at"})),
        file_folder = row["file_path"].split("/")[3] if row["file_path"] != "" else None,
        )

@router.post("/api/recordings", response_model=RecordingGet)
def create_recording(item: Annotated[RecordingPost, Body()], con: DbConnectionDep):
    program_id = get_or_create_program(con, item.program, item.created_at, item.created_at)

    cur = con.execute("""
        INSERT INTO recordings (program_id, file_path, watched_at, deleted_at, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        program_id,
        item.file_path,
        item.watched_at,
        item.deleted_at,
        item.created_at,
    ))
    con.commit()
    return get_recording(cur.lastrowid, con)

@router.patch("/api/recordings/{id}")
def patch_recording(
        item: Annotated[RecordingPatch, Body()], id: Annotated[int, Path()],
        response: Response,
        con: DbConnectionDep, con_factory: DbConnectionFactoryDep, smb: SmbDep, background_tasks: BackgroundTasks):
    diff = item.model_dump(exclude_unset=True)
    accepted = False

    if "deleted_at" in diff and diff["deleted_at"] is not None:
        if "file_path" in diff and diff["file_path"] != "":
            raise HTTPException(status_code=400, detail="Invalid file_path: should be unset")

        file_path, = con.execute("SELECT file_path FROM recordings WHERE id = ?", (id,)).fetchone()
        if file_path != "":
            def delete_file(con_factory):
                smb.delete_files(f"{file_path}*")

                with con_factory() as con:
                    con.execute("UPDATE recordings SET file_path = ? WHERE id = ?", ("", id))
                    con.commit()

            background_tasks.add_task(delete_file, con_factory)
            accepted = True

        item.file_path = diff["file_path"] = ""

    elif "file_folder" in diff:
        if "file_path" in diff:
            raise HTTPException(status_code=400, detail="Invalid file_path: should be unset")

        file_path, = con.execute("SELECT file_path FROM recordings WHERE id = ?", (id,)).fetchone()
        if file_path == "":
            raise HTTPException(status_code=400, detail="No file")

        file_path_splited = file_path.split("/")    # //server/folder/to/file

        if len(file_path_splited) < 3:
            raise HTTPException(status_code=400, detail="Invalid file_path; should be '//server/folder/to/file'")

        file_path_splited[3] = item.file_folder
        item.file_path = diff["file_path"] = "/".join(file_path_splited)

        def move_file(con_factory):
            smb.move_files_by_root(f"{file_path}*", item.file_folder)

            with con_factory() as con:
                con.execute("UPDATE recordings SET file_path = ? WHERE id = ?", (item.file_path, id))
                con.commit()

        background_tasks.add_task(move_file, con_factory)
        accepted = True

    elif "file_path" in diff:
        con.execute("UPDATE recordings SET file_path = ? WHERE id = ?", (item.file_path, id))

    cur = con.execute("""
        UPDATE recordings SET
            watched_at = CASE WHEN :set_watched THEN :watched_at ELSE watched_at END,
            deleted_at = CASE WHEN :set_deleted THEN :deleted_at ELSE deleted_at END
        WHERE id = :id
    """, {
        "id": id,
        "set_watched": "watched_at" in diff,
        "watched_at": item.watched_at,
        "set_deleted": "deleted_at" in diff,
        "deleted_at": item.deleted_at,
    })
    con.commit()
    if accepted:
        response.status_code = status.HTTP_202_ACCEPTED
    return get_recording(id, con)
