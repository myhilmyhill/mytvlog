from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Path, Query, Body, HTTPException, BackgroundTasks, Response, status

from pydantic import BaseModel, Field, computed_field
from datetime import datetime, timedelta
from sqlite3 import Connection
import json
import re
from ..dependencies import JSTDatetime, JST, DbConnectionDep, DbConnectionFactoryDep, SmbDep
from .recordings import import_api, validate

router = APIRouter()
router.include_router(import_api.router)
router.include_router(validate.router)

def extract_model_fields(model: type[BaseModel], row: dict, aliases: dict[str, str] = None) -> dict:
    aliases = aliases or {}
    result = {}
    keys = row.keys()
    for field_name in model.model_fields.keys():
        source_key = aliases.get(field_name, field_name)
        if source_key in keys:
            result[field_name] = row[source_key]
    return result

class ProgramQueryParams(BaseModel):
    page: int = Query(default=1)
    size: int = Query(default=100)
    from_: JSTDatetime | None | Literal[""] = Query(default=None)
    to: JSTDatetime | None | Literal[""] = Query(default=None)
    name: str = Query(default="")

class ProgramBase(BaseModel):
    event_id: int
    service_id: int
    name: str
    start_time: datetime
    duration: int
    text: str | None = None
    ext_text: str | None = None
    created_at: datetime | None = None

class ProgramGetBase(ProgramBase):
    id: int
    created_at: datetime

    @computed_field
    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(seconds=self.duration)

class ProgramGet(ProgramGetBase):
    viewed_times_json: str | None = Field(exclude=True)

    @computed_field
    @property
    def viewed_times(self) -> list[datetime]:
        return [datetime.fromtimestamp(t).astimezone(JST) for t in json.loads(self.viewed_times_json or '[]')]

@router.get("/api/programs", response_model=list[ProgramGet])
def get_programs(params: Annotated[ProgramQueryParams, Depends()], con: DbConnectionDep):
    cur = con.execute("""
        WITH agg_views AS (
            SELECT
                program_id
              , json_group_array(viewed_time) AS viewed_times_json
            FROM views
            GROUP BY program_id
        )
        SELECT
            id
          , event_id
          , service_id
          , name
          , start_time AS "start_time [timestamp]"
          , duration
          , text
          , ext_text
          , created_at AS "created_at [timestamp]"
          , agg_views.viewed_times_json
        FROM programs
        LEFT OUTER JOIN agg_views ON agg_views.program_id = programs.id
        WHERE
            TRUE
          AND (:from IS NULL OR :from <= programs.start_time)
          AND (:to IS NULL OR programs.start_time + programs.duration < :to)
          AND (:name = '' OR programs.name LIKE '%' || :name || '%')
        ORDER BY start_time DESC
        LIMIT :size OFFSET :offset
    """, {
        "from": params.from_ if params.from_ else None,
        "to": params.to + timedelta(days=1) if params.to else None,
        "name": params.name,
        "size": params.size,
        "offset": (params.page - 1) * params.size,
    })
    rows = cur.fetchall()

    return [ProgramGet(**row) for row in rows]

@router.get("/api/programs/{id}", response_model=ProgramGet)
def get_program(id: int, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        WITH agg_views AS (
            SELECT
                program_id
              , json_group_array(viewed_time) AS viewed_times_json
            FROM views
            GROUP BY program_id
        )
        SELECT
            id
          , event_id
          , service_id
          , name
          , start_time AS "start_time [timestamp]"
          , duration
          , text
          , ext_text
          , created_at AS "created_at [timestamp]"
          , agg_views.viewed_times_json
        FROM programs
        LEFT OUTER JOIN agg_views ON agg_views.program_id = programs.id
        WHERE id = ?
    """, (id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404)

    return ProgramGet(**row)

@router.post("/api/programs")
@router.patch("/api/programs/{id}")
def create_program():
    raise NotImplementedError

def get_or_create_program(con: Connection, program: ProgramBase, created_at: datetime, viewed_time: datetime) -> int:
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
        INSERT INTO programs(event_id, service_id, name, start_time, duration, text, ext_text, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
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

class ViewQueryParams(BaseModel):
    program_id: int | None = Query(default=None)
    page: int | None = Query(default=1, gt=0, title="program_id 指定時は無視されて全件取得します")
    size: int | None = Query(default=500, gt=0, title="program_id 指定時は無視されて全件取得します")

class ViewBase(BaseModel):
    viewed_time: datetime
    created_at: datetime

class ViewGet(ViewBase):
    program_id: int

class ViewPost(ViewBase):
    program: ProgramBase
    created_at: datetime = datetime.now()

@router.get("/api/views", response_model=list[ViewGet])
def get_views(params: Annotated[ViewQueryParams, Depends()], con: DbConnectionDep):
    if params.program_id is not None:
        cur = con.execute("""
            SELECT
                program_id
              , viewed_time AS "viewed_time [timestamp]"
              , created_at AS "created_at [timestamp]"
            FROM views
            WHERE program_id = ?
            ORDER BY created_at DESC
        """, (params.program_id,))
        rows = cur.fetchall()
    else:
        offset = (params.page - 1) * params.size
        cur = con.execute("""
            SELECT
                program_id
              , viewed_time AS "viewed_time [timestamp]"
              , created_at AS "created_at [timestamp]"
            FROM views
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (params.size, offset))
        rows = cur.fetchall()

    return [ViewGet(**row) for row in rows]

@router.post("/api/views")
def create_view(item: ViewPost, con: DbConnectionDep):
    program_id = get_or_create_program(con, item.program, item.viewed_time, item.viewed_time)

    cursor = con.cursor()
    cursor.execute("""
        INSERT INTO views(program_id, viewed_time, created_at)
        VALUES(?, ?, ?)
    """, (program_id, item.viewed_time, datetime.now()))
    con.commit()
    return

class RecordingQueryParams(BaseModel):
    program_id: int | None = Query(default=None)
    # TODO: バグでaliasが効かない
    from_: JSTDatetime | None | Literal[""] = Query(default=None, alias="from")
    to: JSTDatetime | None | Literal[""] = Query(default=None)
    watched: bool | Literal["on"] = Query(default=False)
    deleted: bool | Literal["on"] = Query(default=False)
    file_folder: str = Query(default="")

class RecordingBase(BaseModel):
    program: ProgramBase
    file_path: str
    watched_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    file_size: int | None

class RecordingGet(RecordingBase):
    program: ProgramGetBase
    id: int

    @computed_field
    @property
    def file_folder(self) -> str | None:
        s = self.file_path.split("/")
        return s[3] if len(s) > 3 else None

class RecordingPost(RecordingBase):
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

@router.get("/api/recordings", response_model=list[RecordingGet])
def get_recordings(params: Annotated[RecordingQueryParams, Depends()], con: DbConnectionDep):
    cur = con.execute("""
        SELECT
            recordings.id
          , recordings.program_id
          , recordings.file_path
          , recordings.file_size
          , recordings.watched_at AS "watched_at [timestamp]"
          , recordings.deleted_at AS "deleted_at [timestamp]"
          , recordings.created_at AS "created_at [timestamp]"
          , programs.event_id
          , programs.service_id
          , programs.name
          , programs.start_time AS "start_time [timestamp]"
          , programs.duration
          , programs.text
          , programs.ext_text
          , programs.created_at AS "program_created_at [timestamp]"
        FROM recordings INNER JOIN programs ON programs.id = recordings.program_id
        WHERE
            TRUE
          AND (:program_id IS NULL OR programs.id = :program_id)
          AND (:from IS NULL OR :from <= programs.start_time)
          AND (:to IS NULL OR programs.start_time + programs.duration < :to)
          AND (:watched = TRUE OR recordings.watched_at IS NULL)
          AND (:deleted = TRUE OR recordings.deleted_at IS NULL)
          AND (:file_folder = '' OR recordings.file_path REGEXP '^//[^/]+/' || :file_folder || '/.*$')
        ORDER BY programs.start_time DESC, recordings.created_at
    """, {
        "program_id": params.program_id,
        "from": params.from_ if params.from_ else None,
        "to": params.to + timedelta(days=1) if params.to else None,
        "watched": bool(params.watched),
        "deleted": bool(params.deleted),
        "file_folder": params.file_folder,
        })
    rows = cur.fetchall()
    return [
        RecordingGet(
            **extract_model_fields(RecordingGet, row),
            program = ProgramGetBase(
                **extract_model_fields(ProgramGetBase, row, aliases={
                    "created_at": "program_created_at",
                    "id": "program_id",
                })
            )
        )
        for row in rows
        ]

@router.get("/api/recordings/{id}", response_model=RecordingGet)
def get_recording(id: int, con: DbConnectionDep):
    cur = con.execute("""
        SELECT
            recordings.id
          , recordings.program_id
          , recordings.file_path
          , recordings.file_size
          , recordings.watched_at AS "watched_at [timestamp]"
          , recordings.deleted_at AS "deleted_at [timestamp]"
          , recordings.created_at AS "created_at [timestamp]"
          , programs.event_id
          , programs.service_id
          , programs.name
          , programs.start_time AS "start_time [timestamp]"
          , programs.duration
          , programs.text
          , programs.ext_text
          , programs.created_at AS "program_created_at [timestamp]"
        FROM recordings INNER JOIN programs ON programs.id = recordings.program_id
        WHERE recordings.id = ?
    """, (id,))
    row = cur.fetchone()
    if row is None:
        return HTTPException(status_code=404)

    return RecordingGet(
        **extract_model_fields(RecordingGet, row),
        program = ProgramGetBase(
            **extract_model_fields(ProgramGetBase, row, aliases={
                "created_at": "program_created_at",
                "id": "program_id",
                })
            )
        )

@router.post("/api/recordings", response_model=RecordingGet)
def create_recording(item: Annotated[RecordingPost, Body()], con: DbConnectionDep, smb: SmbDep):
    if not re.fullmatch("//[^/]+/[^/]+/.*", item.file_path):
        raise HTTPException(status_code=400, detail="Invalid file_path; should be '//server/folder/to/file'")

    program_id = get_or_create_program(con, item.program, item.created_at, item.created_at)

    cur = con.execute("""
        INSERT INTO recordings(program_id, file_path, file_size, watched_at, deleted_at, created_at)
        VALUES(?, ?, ?, ?, ?, ?)
    """, (
        program_id,
        item.file_path,
        item.file_size,
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
                    con.execute("UPDATE recordings SET file_path = ?, file_size = NULL WHERE id = ?", ("", id))
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
            raise HTTPException(status_code=500, detail="Invalid file_path")

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
        if not re.fullmatch("//[^/]+/[^/]+/.*", diff["file_path"]):
            raise HTTPException(status_code=400, detail="Invalid file_path; should be '//server/folder/to/file'")

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

class Digestion(BaseModel):
    id: int
    name: str
    service_id: int
    start_time: datetime
    duration: int
    viewed_times_json: str | None = Field(exclude=True)

    @computed_field
    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(seconds=self.duration)

    @computed_field
    @property
    def viewed_times(self) -> list[datetime]:
        return [datetime.fromtimestamp(t).astimezone(JST) for t in json.loads(self.viewed_times_json or '[]')]

@router.get("/api/digestions", response_model=list[Digestion])
def get_digestions(con: DbConnectionDep):
    cur = con.execute("""
        WITH agg_views AS (
            SELECT
                program_id
              , json_group_array(viewed_time) AS viewed_times_json
            FROM views
            GROUP BY program_id
        )
        SELECT
            programs.id
          , programs.name
          , programs.service_id
          , programs.start_time
          , programs.duration
          , agg_views.viewed_times_json
        FROM programs
        LEFT OUTER JOIN agg_views ON agg_views.program_id = programs.id
        WHERE
            EXISTS(
                SELECT 1
                FROM recordings
                WHERE program_id = programs.id AND watched_at IS NULL AND deleted_at IS NULL
                )
        ORDER BY programs.start_time
    """)
    rows = cur.fetchall()
    return [Digestion(**row) for row in rows]
