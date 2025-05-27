from typing import Annotated, Literal
from pydantic import BaseModel
from datetime import datetime
import asyncio
from fastapi import APIRouter, Body, Query
from ...dependencies import DbConnectionDep, SmbDep, EdcbDep

router = APIRouter()

class BulkImport(BaseModel):
    event_id: int
    service_id: int
    name: str
    start_time: datetime
    duration: int
    text: str | None = None
    ext_text: str | None = None
    file_path: str = ""
    created_at: datetime = datetime.now()

class ImportRecordingFromJson(BaseModel):
    dry_run: bool
    imports: list[BulkImport]

@router.post("/api/recordings/import-json")
def import_recordings_from_json(body: Annotated[ImportRecordingFromJson, Body()], con: DbConnectionDep, smb: SmbDep):
    return bulk_import(body.model_dump()["imports"], body.dry_run, con, smb)

class ImportRecordingFromEdcb(BaseModel):
    dry_run: bool
    smb_server: str
    recording_created_at: datetime = datetime.now()

@router.post("/api/recordings/import-edcb")
def import_recordings_from_edcb(body: Annotated[ImportRecordingFromEdcb, Body()],
    con: DbConnectionDep, edcb: EdcbDep, smb: SmbDep):
    imports = asyncio.run(edcb.sendEnumRecInfoBasic())
    imports = [{
            "service_id": info["sid"],
            "event_id": info["eid"],
            "name": info["title"],
            "start_time": info["start_time_epg"],
            "duration": info["duration_sec"],
            "text": None,
            "ext_text": None,
            "file_path": f"//{body.smb_server}{info['rec_file_path']}",
            "created_at": body.recording_created_at,
        }
        for info in imports
        if len(info.get("rec_file_path")) > 0
        ]
    return {"count_edcb_recordings": len(imports), **bulk_import(imports, body.dry_run, con, smb)}

def bulk_import(bulk_imports: list[dict], dry_run: bool, con: DbConnectionDep, smb: SmbDep):
    count_input = len(bulk_imports)

    bulk_imports = [{
        **b,
        "file_size": smb.get_file_size(b["file_path"]),
    } for b in bulk_imports if smb.exists(b["file_path"])]

    con.executescript("""
        CREATE TEMP TABLE bulk_imports(
            id INTEGER PRIMARY KEY
          , event_id INTEGER
          , service_id INTEGER
          , name TEXT
          , start_time INTEGER
          , duration INTEGER
          , text TEXT
          , ext_text TEXT
          , file_path TEXT
          , file_size INTEGER
          , created_at INTEGER
        ) STRICT
        ;
        CREATE TEMP TABLE imports_programs(
            id INTEGER PRIMARY KEY
          , event_id INTEGER
          , service_id INTEGER
          , name TEXT
          , start_time INTEGER
          , duration INTEGER
          , text TEXT
          , ext_text TEXT
          , created_at INTEGER
        ) STRICT
        ;
        CREATE TEMP TABLE imports_recordings(
            id INTEGER PRIMARY KEY
          , temp_program_id INTEGER
          , existing_program_id INTEGER
          , file_path TEXT
          , file_size INTEGER
          , created_at INTEGER
        ) STRICT
        ;
    """)

    con.executemany("""
        INSERT INTO bulk_imports(event_id, service_id, name, start_time, duration, text, ext_text, file_path, file_size, created_at)
        VALUES(:event_id, :service_id, :name, :start_time, :duration, :text, :ext_text, :file_path, :file_size, :created_at)
    """, bulk_imports)

    count_programs = con.execute("""
        INSERT INTO imports_programs(event_id, service_id, name, start_time, duration, text, ext_text, created_at)
        SELECT
            event_id, service_id, name, start_time, duration, text, ext_text, created_at
        FROM bulk_imports b
        WHERE NOT EXISTS (
            SELECT 1
            FROM programs
            WHERE event_id = event_id AND service_id = b.service_id AND start_time = b.start_time
        )
    """).rowcount
    count_recordings = con.execute("""
        INSERT INTO imports_recordings(temp_program_id, existing_program_id, file_path, file_size, created_at)
        SELECT
            ip.id, p.id, b.file_path, b.file_size, b.created_at
        FROM bulk_imports b
        LEFT OUTER JOIN imports_programs AS ip ON
            ip.event_id = b.event_id
          AND ip.service_id = b.service_id
          AND ip.start_time = b.start_time
        LEFT OUTER JOIN programs AS p ON
            ip.id IS NULL
          AND p.event_id = b.event_id
          AND p.service_id = b.service_id
          AND p.start_time = b.start_time
        WHERE NOT EXISTS (SELECT 1 FROM recordings WHERE file_path = b.file_path)
    """).rowcount
    count_programs = count_programs - con.execute("""
        DELETE FROM imports_programs WHERE id NOT IN (SELECT temp_program_id FROM imports_recordings)
    """).rowcount

    if dry_run:
        try:
            cur = con.execute("""
                SELECT
                    ir.temp_program_id
                  , ir.existing_program_id
                  , coalesce(p.event_id, ip.event_id) AS event_id
                  , coalesce(p.service_id, ip.service_id) AS service_id
                  , coalesce(p.name, ip.name) AS name
                  , coalesce(p.start_time, ip.start_time) AS "start_time [timestamp]"
                  , coalesce(p.duration, ip.duration) AS duration
                  , coalesce(p.text, ip.text) AS text
                  , coalesce(p.ext_text, ip.ext_text) AS ext_text
                  , ir.id AS new_recording_id
                  , ir.file_path
                  , ir.file_size
                  , ir.created_at AS "created_at [timestamp]"
                FROM imports_recordings AS ir
                LEFT OUTER JOIN imports_programs ip ON ip.id = ir.temp_program_id
                LEFT OUTER JOIN programs p ON p.id = ir.existing_program_id
            """)
            return {
                "count_programs": count_programs,
                "count_recordings": count_recordings,
                "preview_imports": cur.fetchall(),
            }
        finally:
            con.rollback()

    con.executescript("""
        INSERT INTO programs(event_id, service_id, name, start_time, duration, text, ext_text, created_at)
        SELECT event_id, service_id, name, start_time, duration, text, ext_text, created_at
        FROM imports_programs
        ;
        INSERT INTO recordings(program_id, file_path, file_size, created_at)
        SELECT p.id, ir.file_path, ir.file_size, ir.created_at
        FROM imports_recordings AS ir
        LEFT OUTER JOIN imports_programs AS ip ON ip.id = ir.temp_program_id
        LEFT OUTER JOIN programs AS p ON p.id = ir.existing_program_id
          OR p.event_id = ip.event_id
          AND p.service_id = ip.service_id
          AND p.start_time = ip.start_time
        ;
    """)
    con.commit()

    return {"count_programs": count_programs, "count_recordings": count_recordings}
