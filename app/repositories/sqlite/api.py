from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlite3 import Connection
import re
from ...models.api import ProgramBase, ProgramQueryParams, ProgramGetBase, ProgramGet, ViewBase, ViewQueryParams, ViewGet, RecordingBase, RecordingQueryParams, RecordingGet, Digestion
from ..interfaces import ProgramRepository, ViewRepository, RecordingRepository, DigestionRepository
from ..exceptions import NotFoundError, InvalidDataError, UnexpectedError
from ..utils import extract_model_fields

class SQLiteProgramRepository(ProgramRepository):
    def __init__(self, con: Connection):
        self.con = con

    def search(self, params: ProgramQueryParams) -> list[ProgramGet]:
        cur = self.con.execute("""
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

    def get_by_id(self, id: int) -> ProgramGet | None:
        cur = self.con.cursor()
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
        return ProgramGet(**row) if row is not None else None

    def get_or_create(self, program: ProgramBase, created_at: datetime, viewed_time: datetime) -> int:
        cur = self.con.cursor()
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

class SQLiteViewRepository(ViewRepository):
    def __init__(self, con: Connection):
        self.con = con

    def search(self, params: ViewQueryParams) -> list[ViewGet]:
        if params.program_id is not None:
            cur = self.con.execute("""
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
            cur = self.con.execute("""
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

    def create(self, program_id: int, view: ViewBase) -> None:
        cursor = self.con.cursor()
        cursor.execute("""
            INSERT INTO views(program_id, viewed_time, created_at)
            VALUES(?, ?, ?)
        """, (program_id, view.viewed_time, datetime.now()))
        self.con.commit()

class SQLiteRecordingRepository(RecordingRepository):
    def __init__(self, con: Connection):
        self.con = con

    def search(self, params: RecordingQueryParams) -> list[RecordingGet]:
        cur = self.con.execute("""
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

    def get_by_id(self, id: int) -> RecordingGet:
        cur = self.con.execute("""
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
            return None

        return RecordingGet(
            **extract_model_fields(RecordingGet, row),
            program = ProgramGetBase(
                **extract_model_fields(ProgramGetBase, row, aliases={
                    "created_at": "program_created_at",
                    "id": "program_id",
                    })
                )
            )

    def create(self, recording: RecordingBase, program_id: int) -> int:
        if not re.fullmatch("//[^/]+/[^/]+/.*", recording.file_path):
            raise InvalidDataError(detail="Invalid file_path; should be '//server/folder/to/file'")

        cur = self.con.execute("""
            INSERT INTO recordings(program_id, file_path, file_size, watched_at, deleted_at, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
        """, (
            program_id,
            recording.file_path,
            recording.file_size,
            recording.watched_at,
            recording.deleted_at,
            recording.created_at,
        ))
        self.con.commit()
        return cur.lastrowid

    def update_patch(self, id: int, patch: dict, smb, background_tasks, con_factory) -> bool:
        diff = patch.model_dump(exclude_unset=True)
        accepted = False

        if "deleted_at" in diff and diff["deleted_at"] is not None:
            if "file_path" in diff and diff["file_path"] != "":
                raise InvalidDataError(detail="Invalid file_path: should be unset")

            file_path, = self.con.execute("SELECT file_path FROM recordings WHERE id = ?", (id,)).fetchone()
            if file_path != "":
                def delete_file(con_factory):
                    smb.delete_files(f"{file_path}*")

                    with con_factory() as con:
                        con.execute("UPDATE recordings SET file_path = ?, file_size = NULL WHERE id = ?", ("", id))
                        con.commit()

                background_tasks.add_task(delete_file, con_factory)
                accepted = True

            patch.file_path = diff["file_path"] = ""

        elif "file_folder" in diff:
            if "file_path" in diff:
                raise InvalidDataError(detail="Invalid file_path: should be unset")

            file_path, = self.con.execute("SELECT file_path FROM recordings WHERE id = ?", (id,)).fetchone()
            if file_path == "":
                raise NotFoundError()

            file_path_splited = file_path.split("/")    # //server/folder/to/file

            if len(file_path_splited) < 3:
                raise UnexpectedError(detail="Invalid file_path")

            file_path_splited[3] = patch.file_folder
            patch.file_path = diff["file_path"] = "/".join(file_path_splited)

            def move_file(con_factory):
                smb.move_files_by_root(f"{file_path}*", patch.file_folder)

                with con_factory() as con:
                    con.execute("UPDATE recordings SET file_path = ? WHERE id = ?", (patch.file_path, id))
                    con.commit()

            background_tasks.add_task(move_file, con_factory)
            accepted = True

        elif "file_path" in diff:
            if not re.fullmatch("//[^/]+/[^/]+/.*", diff["file_path"]):
                raise InvalidDataError(detail="Invalid file_path; should be '//server/folder/to/file'")

            self.con.execute("UPDATE recordings SET file_path = ? WHERE id = ?", (patch.file_path, id))

        cur = self.con.execute("""
            UPDATE recordings SET
                watched_at = CASE WHEN :set_watched THEN :watched_at ELSE watched_at END,
                deleted_at = CASE WHEN :set_deleted THEN :deleted_at ELSE deleted_at END
            WHERE id = :id
        """, {
            "id": id,
            "set_watched": "watched_at" in diff,
            "watched_at": patch.watched_at,
            "set_deleted": "deleted_at" in diff,
            "deleted_at": patch.deleted_at,
        })
        self.con.commit()
        return accepted

class SQLiteDigestionRepository(DigestionRepository):
    def __init__(self, con: Connection):
        self.con = con

    def list_digestions(self) -> list[Digestion]:
        cur = self.con.execute("""
            WITH agg_views AS (
                SELECT
                    program_id
                , json_group_array(viewed_time) AS viewed_times_json
                , COUNT(viewed_time) * 5 * 60 AS viewed_seconds
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
              AND COALESCE(agg_views.viewed_seconds, 0) < programs.duration * 0.8
            ORDER BY programs.start_time
        """)
        rows = cur.fetchall()
        return [Digestion(**row) for row in rows]
