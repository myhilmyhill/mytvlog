from datetime import datetime, timedelta
import re
import uuid
from google.cloud import bigquery
from ...models.api import ProgramBase, ProgramQueryParams, ProgramGetBase, ProgramGet, ViewBase, ViewQueryParams, ViewGet, RecordingBase, RecordingQueryParams, RecordingGet, Series, Digestion
from ..interfaces import ProgramRepository, ViewRepository, RecordingRepository, SeriesRepository, DigestionRepository
from ..exceptions import InvalidDataError, NotFoundError, UnexpectedError
from ..utils import extract_model_fields

class BigQueryBaseRepository:
    def __init__(self, project_id: str, dataset_id: str):
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
        self.dataset_id = dataset_id

    def _make_query_job_config(self, query_parameters=None) -> bigquery.QueryJobConfig:
        return bigquery.QueryJobConfig(
            query_parameters=query_parameters or [],
            default_dataset=f"{self.project_id}.{self.dataset_id}",
        )

class BigQueryProgramRepository(BigQueryBaseRepository, ProgramRepository):
    def __init__(self, project_id: str, dataset_id: str):
        super().__init__(project_id, dataset_id)

    def search(self, params: ProgramQueryParams) -> list[ProgramGet]:
        query_params = {
            "from": params.from_ or None,
            "to": params.to + timedelta(days=1) if params.to else None,
            "name": params.name or '',
            "size": params.size,
            "offset": (params.page - 1) * params.size,
        }
        job = self.client.query("""
WITH agg_views AS (
    SELECT
        program_id,
        TO_JSON_STRING(ARRAY_AGG(viewed_time)) AS viewed_times_json
    FROM views
    GROUP BY program_id
)
SELECT
    programs.id,
    programs.event_id,
    programs.service_id,
    programs.name,
    programs.start_time,
    programs.duration,
    programs.text,
    programs.ext_text,
    programs.created_at,
    agg_views.viewed_times_json
FROM programs
LEFT JOIN agg_views ON agg_views.program_id = programs.id
WHERE
    TRUE
    AND (@from IS NULL OR @from <= programs.start_time)
    AND (@to IS NULL OR TIMESTAMP_ADD(programs.start_time, INTERVAL programs.duration SECOND) < @to)
    AND (@name = '' OR programs.name LIKE CONCAT('%', @name, '%'))
ORDER BY programs.start_time DESC
LIMIT @size OFFSET @offset
            """,
            job_config=self._make_query_job_config(query_parameters=[
                bigquery.ScalarQueryParameter("from", "TIMESTAMP", query_params["from"]),
                bigquery.ScalarQueryParameter("to", "TIMESTAMP", query_params["to"]),
                bigquery.ScalarQueryParameter("name", "STRING", query_params["name"]),
                bigquery.ScalarQueryParameter("size", "INT64", query_params["size"]),
                bigquery.ScalarQueryParameter("offset", "INT64", query_params["offset"]),
        ]))
        rows = job.result()

        return [ProgramGet(**row) for row in rows]

    def get_by_id(self, id: str) -> ProgramGet | None:
        job = self.client.query("""
            WITH agg_views AS (
            SELECT
                program_id,
                TO_JSON_STRING(ARRAY_AGG(viewed_time)) AS viewed_times_json
            FROM views
            GROUP BY program_id
            )
            SELECT
            p.id,
            p.event_id,
            p.service_id,
            p.name,
            p.start_time,
            p.duration,
            p.text,
            p.ext_text,
            p.created_at,
            agg_views.viewed_times_json
            FROM programs p
            LEFT JOIN agg_views ON agg_views.program_id = p.id
            WHERE p.id = @id
            """,
            job_config=self._make_query_job_config(query_parameters=[
                bigquery.ScalarQueryParameter("id", "STRING", id)
        ]))
        row = next(job.result(), None)
        return ProgramGet(**row) if row is not None else None

    def get_or_create(self, program: ProgramBase, created_at: datetime, viewed_time: datetime) -> int:
        job = self.client.query("""
            SELECT id, duration, created_at
            FROM programs
            WHERE event_id = @event_id
            AND service_id = @service_id
            AND start_time = @start_time
            """, job_config=self._make_query_job_config(query_parameters=[
                bigquery.ScalarQueryParameter("event_id", "INT64", program.event_id),
                bigquery.ScalarQueryParameter("service_id", "INT64", program.service_id),
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", program.start_time),
        ]))
        row = next(job.result(), None)

        if row:
            id_, duration, created_at_in_db = row
            if duration != program.duration and created_at_in_db < viewed_time:
                self.client.query("""
                    UPDATE programs
                    SET duration = @new_duration
                    WHERE id = @id
                    """, job_config=self._make_query_job_config(query_parameters=[
                        bigquery.ScalarQueryParameter("new_duration", "INT64", program.duration),
                        bigquery.ScalarQueryParameter("id", "STRING", id_)
                ])).result()
            return id_

        new_id = str(uuid.uuid4())

        self.client.query("""
            INSERT INTO programs (
                id, event_id, service_id, name, start_time,
                duration, text, ext_text, created_at
            )
            VALUES (
                @id, @event_id, @service_id, @name, @start_time,
                @duration, @text, @ext_text, @created_at
            )
            """, job_config=self._make_query_job_config(query_parameters=[
                bigquery.ScalarQueryParameter("id", "STRING", new_id),
                bigquery.ScalarQueryParameter("event_id", "INT64", program.event_id),
                bigquery.ScalarQueryParameter("service_id", "INT64", program.service_id),
                bigquery.ScalarQueryParameter("name", "STRING", program.name),
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", program.start_time),
                bigquery.ScalarQueryParameter("duration", "INT64", program.duration),
                bigquery.ScalarQueryParameter("text", "STRING", program.text),
                bigquery.ScalarQueryParameter("ext_text", "STRING", program.ext_text),
                bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", created_at),
        ])).result()

        return new_id

class BigQueryViewRepository(BigQueryBaseRepository, ViewRepository):
    def __init__(self, project_id: str, dataset_id: str):
        super().__init__(project_id, dataset_id)

    def search(self, params: ViewQueryParams) -> list[ViewGet]:
        if params.program_id is not None:
            query = """
            SELECT
                program_id,
                viewed_time,
                created_at
            FROM views
            WHERE program_id = @program_id
            ORDER BY created_at DESC
            """
            qparams = [bigquery.ScalarQueryParameter("program_id", "STRING", params.program_id)]
        else:
            offset = (params.page - 1) * params.size
            query = """
            SELECT
                program_id,
                viewed_time,
                created_at
            FROM views
            ORDER BY created_at DESC
            LIMIT @size OFFSET @offset
            """
            qparams = [
                bigquery.ScalarQueryParameter("size", "INT64", params.size),
                bigquery.ScalarQueryParameter("offset", "INT64", offset),
            ]

        rows = self.client.query(query, job_config=self._make_query_job_config(query_parameters=qparams)).result()
        return [ViewGet(**dict(row)) for row in rows]

    def create(self, program_id: str, view: ViewBase) -> None:
        query = """
        INSERT INTO views(program_id, viewed_time, created_at)
        VALUES(@program_id, @viewed_time, @created_at)
        """
        self.client.query(query, job_config=self._make_query_job_config(query_parameters=[
            bigquery.ScalarQueryParameter("program_id", "STRING", program_id),
            bigquery.ScalarQueryParameter("viewed_time", "TIMESTAMP", view.viewed_time),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", datetime.now()),
        ])).result()


class BigQueryRecordingRepository(BigQueryBaseRepository, RecordingRepository):
    def __init__(self, project_id: str, dataset_id: str):
        super().__init__(project_id, dataset_id)

    def search(self, params: RecordingQueryParams) -> list[RecordingGet]:
        job = self.client.query("""
            SELECT
                r.id,
                r.program_id,
                r.file_path,
                r.file_size,
                r.watched_at,
                r.deleted_at,
                r.created_at,
                p.event_id,
                p.service_id,
                p.name,
                p.start_time,
                p.duration,
                p.text,
                p.ext_text,
                p.created_at AS program_created_at
            FROM recordings r
            JOIN programs p ON p.id = r.program_id
            WHERE
                (@program_id IS NULL OR p.id = @program_id)
                AND (@from IS NULL OR p.start_time >= @from)
                --AND (@to IS NULL OR TIMESTAMP_ADD(p.start_time, INTERVAL p.duration SECOND) < @to)
                AND (@watched = TRUE OR r.watched_at IS NULL)
                AND (@deleted = TRUE OR r.deleted_at IS NULL)
                AND (@file_folder = '' OR REGEXP_CONTAINS(r.file_path, CONCAT('^//[^/]+/', @file_folder, '/.*$')))
            ORDER BY p.start_time DESC, r.created_at
            """, job_config=self._make_query_job_config(query_parameters=[
                bigquery.ScalarQueryParameter("program_id", "STRING", params.program_id),
                bigquery.ScalarQueryParameter("from", "TIMESTAMP", params.from_ or None),
                bigquery.ScalarQueryParameter("to", "TIMESTAMP", params.to + timedelta(days=1) if params.to else None),
                bigquery.ScalarQueryParameter("watched", "BOOL", bool(params.watched)),
                bigquery.ScalarQueryParameter("deleted", "BOOL", bool(params.deleted)),
                bigquery.ScalarQueryParameter("file_folder", "STRING", params.file_folder or '')
        ]))
        rows = job.result()
        return [
            RecordingGet(
                **extract_model_fields(RecordingGet, row),
                program=ProgramGetBase(
                    **extract_model_fields(ProgramGetBase, row, aliases={
                        "created_at": "program_created_at",
                        "id": "program_id",
                    })
                )
            ) for row in rows
        ]

    def get_by_id(self, id: str) -> RecordingGet:
        row = next(self.client.query("""
            SELECT
                r.id,
                r.program_id,
                r.file_path,
                r.file_size,
                r.watched_at,
                r.deleted_at,
                r.created_at,
                p.event_id,
                p.service_id,
                p.name,
                p.start_time,
                p.duration,
                p.text,
                p.ext_text,
                p.created_at AS program_created_at
            FROM recordings r
            JOIN programs p ON p.id = r.program_id
            WHERE r.id = @id
            """, job_config=self._make_query_job_config(query_parameters=[
                bigquery.ScalarQueryParameter("id", "STRING", id)
        ])).result(), None)
        if row is None:
            return None

        return RecordingGet(
            **extract_model_fields(RecordingGet, row),
            program=ProgramGetBase(
                **extract_model_fields(ProgramGetBase, row, aliases={
                    "created_at": "program_created_at",
                    "id": "program_id",
                })
            )
        )

    def create(self, recording: RecordingBase, program_id: str) -> str:
        if not re.fullmatch("//[^/]+/[^/]+/.*", recording.file_path):
            raise InvalidDataError(detail="Invalid file_path; should be '//server/folder/to/file'")

        new_id = str(uuid.uuid4())
        self.client.query("""
            INSERT INTO recordings(id, program_id, file_path, file_size, watched_at, deleted_at, created_at)
            VALUES(@id, @program_id, @file_path, @file_size, @watched_at, @deleted_at, @created_at)
            """, job_config=self._make_query_job_config(query_parameters=[
                bigquery.ScalarQueryParameter("id", "STRING", new_id),
                bigquery.ScalarQueryParameter("program_id", "STRING", program_id),
                bigquery.ScalarQueryParameter("file_path", "STRING", recording.file_path),
                bigquery.ScalarQueryParameter("file_size", "INT64", recording.file_size),
                bigquery.ScalarQueryParameter("watched_at", "TIMESTAMP", recording.watched_at),
                bigquery.ScalarQueryParameter("deleted_at", "TIMESTAMP", recording.deleted_at),
                bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", recording.created_at)
        ])).result()
        return new_id

    def update_patch(self, id: str, patch: dict) -> bool:
        diff = patch.model_dump(exclude_unset=True)

        # Handle deleted_at
        if "deleted_at" in diff and diff["deleted_at"] is not None:
            if "file_path" in diff and diff["file_path"] != "":
                raise InvalidDataError(detail="Invalid file_path: should be unset")
            
            # Set file_path to empty string when deleting
            patch.file_path = diff["file_path"] = ""

        # Handle file_folder - convert to file_path
        elif "file_folder" in diff:
            if "file_path" in diff:
                raise InvalidDataError(detail="Invalid file_path: should be unset")

            row = next(self.client.query("""
                SELECT file_path FROM recordings WHERE id = @id
                """, job_config=self._make_query_job_config(query_parameters=[
                    bigquery.ScalarQueryParameter("id", "STRING", id)
            ])).result(), None)
            
            if row is None:
                raise NotFoundError()
            
            file_path = row["file_path"]
            if file_path == "":
                raise NotFoundError()

            file_path_splited = file_path.split("/")    # //server/folder/to/file

            if len(file_path_splited) < 4:
                raise UnexpectedError(detail="Invalid file_path")

            file_path_splited[3] = patch.file_folder
            patch.file_path = diff["file_path"] = "/".join(file_path_splited)

        # Validate file_path if provided
        elif "file_path" in diff:
            if not re.fullmatch("//[^/]+/[^/]+/.*", diff["file_path"]):
                raise InvalidDataError(detail="Invalid file_path; should be '//server/folder/to/file'")

        # Build UPDATE query dynamically
        update_parts = []
        query_params = [bigquery.ScalarQueryParameter("id", "STRING", id)]
        
        if "file_path" in diff:
            update_parts.append("file_path = @file_path")
            query_params.append(bigquery.ScalarQueryParameter("file_path", "STRING", patch.file_path))
            
            # If file_path is being set to empty, also set file_size to NULL
            if patch.file_path == "":
                update_parts.append("file_size = NULL")
        
        if "watched_at" in diff:
            update_parts.append("watched_at = @watched_at")
            query_params.append(bigquery.ScalarQueryParameter("watched_at", "TIMESTAMP", patch.watched_at))
        
        if "deleted_at" in diff:
            update_parts.append("deleted_at = @deleted_at")
            query_params.append(bigquery.ScalarQueryParameter("deleted_at", "TIMESTAMP", patch.deleted_at))
        
        if update_parts:
            query = f"""
                UPDATE recordings 
                SET {', '.join(update_parts)}
                WHERE id = @id
            """
            self.client.query(query, job_config=self._make_query_job_config(query_parameters=query_params)).result()
        
        return False

class BigQuerySeriesRepository(BigQueryBaseRepository, SeriesRepository):
    def __init__(self, project_id: str, dataset_id: str):
        super().__init__(project_id, dataset_id)

    def search(self) -> list[Series]:
        pass

class BigQueryDigestionRepository(BigQueryBaseRepository, DigestionRepository):
    def __init__(self, project_id: str, dataset_id: str):
        super().__init__(project_id, dataset_id)
        
    def list_digestions(self) -> list[Digestion]:
        rows = self.client.query("""
            WITH agg_views AS (
                SELECT
                    program_id,
                    TO_JSON_STRING(ARRAY_AGG(viewed_time)) AS viewed_times_json,
                    COUNT(viewed_time) * 5 * 60 AS viewed_seconds
                FROM views
                GROUP BY program_id
            )
            SELECT
                p.id,
                p.name,
                p.service_id,
                p.start_time,
                p.duration,
                agg.viewed_times_json
            FROM programs p
            LEFT JOIN agg_views agg ON agg.program_id = p.id
            WHERE EXISTS (
                SELECT 1 FROM recordings r WHERE r.program_id = p.id AND r.watched_at IS NULL AND r.deleted_at IS NULL
            )
              AND COALESCE(agg.viewed_seconds, 0) < p.duration * 0.8
            ORDER BY p.start_time
            """, job_config=self._make_query_job_config()).result()
        return [Digestion(**dict(row)) for row in rows]
