from typing import Annotated
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.gzip import GZipMiddleware
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import os
from .dependencies import DigestionRepositoryDep, ProgramRepositoryDep, RecordingRepositoryDep, SeriesRepositoryDep, ViewRepositoryDep
from .middlewares.firebase_auth import FirebaseAuthMiddleware
from .routers import api, auth

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(FirebaseAuthMiddleware)
app.include_router(api.router)
app.include_router(auth.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["config"] = {
    "TVREMOCON_API_URL": os.getenv("TVREMOCON_API_URL", "/play")
}

dst_root = os.getenv("dst_root")

@app.get("/", response_class=HTMLResponse)
def show_auth_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="auth.html", context={
            "api_key": os.environ["IDENTITY_PLATFORM_API_KEY"],
            "auth_domain": os.environ["IDENTITY_PLATFORM_AUTH_DOMAIN"],
        },
        headers={
            "Cache-Control": "public, max-age=2592000"
        })

@app.get("/digestions", response_class=HTMLResponse)
def digestions(request: Request, dig_repo: DigestionRepositoryDep):
    digestions = [{
        **d.model_dump(),
        "start_time_timestamp": int(d.start_time.timestamp()),
        "end_time_timestamp": int(d.end_time.timestamp()),
        "viewed_times_timestamp": [int(t.timestamp()) for t in d.viewed_times],
    } for d in api.get_digestions(dig_repo)]

    return templates.TemplateResponse(
        request=request, name="digestions.html", context={"digestions": digestions, "dst_root": dst_root})

@app.get("/programs", response_class=HTMLResponse)
def programs(request: Request,
             params: Annotated[api.ProgramQueryParams, Depends()],
             prog_repo: ProgramRepositoryDep):
    programs = [{
        **p.model_dump(),
        "start_time_timestamp": int(p.start_time.timestamp()),
        "end_time_timestamp": int(p.end_time.timestamp()),
        "viewed_times_timestamp": [int(t.timestamp()) for t in p.viewed_times],
    } for p in api.get_programs(params, prog_repo)]

    return templates.TemplateResponse(
        request=request, name="programs.html", context={"programs": programs, "params": params})

@app.get("/recordings", response_class=HTMLResponse)
def recordings(request: Request,
               params: Annotated[api.RecordingQueryParams, Depends()],
               rec_repo: RecordingRepositoryDep):
    recordings = api.get_recordings(params, rec_repo)

    return templates.TemplateResponse(
        request=request, name="recordings.html", context={"recordings": recordings})

@app.get("/views", response_class=HTMLResponse)
def views(request: Request,
          params: Annotated[api.ViewQueryParams, Depends()],
          view_repo: ViewRepositoryDep):
    views = api.get_views(params, view_repo)

    return templates.TemplateResponse(
        request=request, name="views.html", context={"views": views, "params": params})

@app.get("/series", response_class=HTMLResponse)
def views(request: Request,
          params: Annotated[api.SeriesQueryParams, Depends()],
          series_repo: SeriesRepositoryDep):
    series = api.get_series(params, series_repo)

    return templates.TemplateResponse(
        request=request, name="series.html", context={"series": series, "params": params})
