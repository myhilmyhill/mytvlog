import re
import os
from datetime import datetime
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Path, Body, HTTPException, Response, status

from ..models.api import ProgramQueryParams, ProgramGet, Series, SeriesAddProgram, SeriesPost, SeriesWithPrograms, ViewQueryParams, ViewGet, ViewPost, RecordingQueryParams, RecordingGet, RecordingPost, RecordingPatch, SeriesQueryParams, Digestion, SeriesPatch, SeriesProgramPatch, DigestionQueryParams
from ..dependencies import DigestionRepositoryDep, ProgramRepositoryDep, RecordingRepositoryDep, ViewRepositoryDep, SeriesRepositoryDep
from ..repositories.utils import extract_series_title, extract_series_title_llm
from ..repositories.exceptions import InvalidDataError, NotFoundError, UnexpectedError

router = APIRouter()

@router.get("/api/programs", response_model=list[ProgramGet])
def get_programs(params: Annotated[ProgramQueryParams, Depends()], repo: ProgramRepositoryDep):
    return repo.search(params)

@router.get("/api/programs/{id}", response_model=ProgramGet)
def get_program(id: int | str, repo: ProgramRepositoryDep):
    program = repo.get_by_id(id)
    if program is None:
        raise HTTPException(status_code=404)

    return program

@router.post("/api/programs")
@router.patch("/api/programs/{id}")
def create_program():
    raise NotImplementedError

@router.get("/api/views", response_model=list[ViewGet])
def get_views(params: Annotated[ViewQueryParams, Depends()], view_repo: ViewRepositoryDep):
    return view_repo.search(params)

@router.post("/api/views")
def create_view(item: ViewPost, prog_repo: ProgramRepositoryDep, view_repo: ViewRepositoryDep):
    program_id = prog_repo.get_or_create(item.program, item.viewed_time, item.viewed_time)
    view_repo.create(program_id, item)
    return

@router.get("/api/recordings", response_model=list[RecordingGet])
def get_recordings(params: Annotated[RecordingQueryParams, Depends()], rec_repo: RecordingRepositoryDep):
    return rec_repo.search(params)

@router.get("/api/recordings/{id}", response_model=RecordingGet)
def get_recording(id: int | str, rec_repo: RecordingRepositoryDep):
    return rec_repo.get_by_id(id)

@router.post("/api/recordings", response_model=RecordingGet)
async def create_recording(item: Annotated[RecordingPost, Body()], prog_repo: ProgramRepositoryDep, rec_repo: RecordingRepositoryDep, series_repo: SeriesRepositoryDep):
    if not re.fullmatch("//[^/]+/[^/]+/.*", item.file_path):
        raise HTTPException(status_code=400, detail="Invalid file_path; should be '//server/folder/to/file'")

    program_id = prog_repo.get_or_create(item.program, item.created_at, item.created_at)
    id_ = rec_repo.create(item, program_id)

    try:
        series_name = await extract_series_title_llm(
            item.program.name,
            api_key=os.getenv("GEMINI_API_KEY")
        )
    except Exception as e:
        print(f"LLM extraction failed: {e}")
        series_name = extract_series_title(item.program.name)

    print(f"Extracted series name: {series_name}")
    series_id = series_repo.get_or_create(series_name, item.created_at)
    series_repo.add_program(series_id, program_id, item.created_at)

    return rec_repo.get_by_id(id_)

@router.patch("/api/recordings/{id}")
def patch_recording(
        item: Annotated[RecordingPatch, Body()], id: Annotated[int | str, Path()],
        response: Response,
        rec_repo: RecordingRepositoryDep):
    try:
        accepted = rec_repo.update_patch(id, item)
        if accepted:
            response.status_code = status.HTTP_202_ACCEPTED
        return rec_repo.get_by_id(id)
    except InvalidDataError as e:
        raise HTTPException(status_code=400, detail=e.detail)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except UnexpectedError as e:
        raise HTTPException(status_code=500, detail=e.detail)

@router.get("/api/digestions", response_model=list[Digestion])
def get_digestions(params: Annotated[DigestionQueryParams, Depends()], dig_repo: DigestionRepositoryDep):
    return dig_repo.list_digestions(params)

@router.get("/api/series", response_model=list[Series])
def get_series(params: Annotated[SeriesQueryParams, Depends()], series_repo: SeriesRepositoryDep):
    return series_repo.search(params)

@router.post("/api/series", response_model=Series)
def create_series(params: Annotated[SeriesPost, Body()], series_repo: SeriesRepositoryDep):
    id_ = series_repo.create(params.name, params.created_at)
    return series_repo.get_by_id(id_)

@router.get("/api/series/{id}", response_model=SeriesWithPrograms)
def get_series_by_id(id: int | str, series_repo: SeriesRepositoryDep):
    try:
        series = series_repo.get_by_id(id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail)
    return series

@router.patch("/api/series/{id}", response_model=SeriesWithPrograms)
def update_series(id: int | str, item: SeriesPatch, series_repo: SeriesRepositoryDep):
    series_repo.update(id, item.name)
    return series_repo.get_by_id(id)

@router.post("/api/series/{id}/programs")
def add_program_to_series(id: int | str, params: SeriesAddProgram, series_repo: SeriesRepositoryDep):
    try:
        series_repo.add_program(id, params.program_id, datetime.now())
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail)
    return

@router.patch("/api/series/{series_id}/programs/{program_id}", response_model=SeriesWithPrograms)
def update_program_series(
    series_id: int | str,
    program_id: int | str,
    item: SeriesProgramPatch,
    series_repo: SeriesRepositoryDep
):
    series_repo.update_program_series(program_id, series_id, item.series_name)
    return series_repo.get_by_id(series_id)
