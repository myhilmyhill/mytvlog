from typing import Annotated
from fastapi import FastAPI, Request, Depends
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import os
from .dependencies import DigestionRepositoryDep, ProgramRepositoryDep, RecordingRepositoryDep, ViewRepositoryDep
from .middlewares.firebase_auth import FirebaseAuthMiddleware
from .routers import api

app = FastAPI()
app.add_middleware(FirebaseAuthMiddleware)
app.include_router(api.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

dst_root = os.environ["dst_root"]

@app.get("/", response_class=HTMLResponse)
def auth(request: Request):
    return templates.TemplateResponse(
        request=request, name="auth.html", context={
            "api_key": os.environ["IDENTITY_PLATFORM_API_KEY"],
            "auth_domain": os.environ["IDENTITY_PLATFORM_AUTH_DOMAIN"],
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
