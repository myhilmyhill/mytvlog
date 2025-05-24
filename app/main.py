from typing import Annotated
from fastapi import FastAPI, Request, Depends
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import json
import os
from datetime import datetime
from .dependencies import DbConnectionDep
from .routers import api

app = FastAPI()
app.include_router(api.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

dst_root = os.environ["dst_root"]

@app.get("/", response_class=HTMLResponse)
def digestions(request: Request, con: DbConnectionDep):
    digestions_raw = api.get_digestions(con)
    digestions = []
    for d in digestions_raw:
        d_dict = d.model_dump()
        d_dict["start_time_timestamp"] = int(d.start_time.timestamp())
        d_dict["end_time_timestamp"] = int(d.end_time.timestamp())
        d_dict["viewed_times_timestamp"] = [int(t.timestamp()) for t in d.viewed_times]
        digestions.append(d_dict)
    return templates.TemplateResponse(
        request=request, name="index.html", context={"digestions": digestions, "dst_root": dst_root})

@app.get("/programs", response_class=HTMLResponse)
def programs(request: Request, params: Annotated[api.ProgramQueryParams, Depends()], con: DbConnectionDep):
    programs_raw = api.get_programs(params, con)
    programs = []
    for p in programs_raw:
        p_dict = p.model_dump()
        p_dict["start_time_timestamp"] = int(p.start_time.timestamp())
        p_dict["end_time_timestamp"] = int(p.end_time.timestamp())
        p_dict["viewed_times_timestamp"] = [int(t.timestamp()) for t in p.viewed_times]
        programs.append(p_dict)

    return templates.TemplateResponse(
        request=request, name="programs.html", context={"programs": programs, "params": params})

class RecordingQueryParams(api.RecordingQueryParams):
    watched: bool = False

@app.get("/recordings", response_class=HTMLResponse)
def recordings(request: Request, params: Annotated[RecordingQueryParams, Depends()], con: DbConnectionDep):
    recordings = api.get_recordings(params, con)

    return templates.TemplateResponse(
        request=request, name="recordings.html", context={"recordings": recordings})

@app.get("/views", response_class=HTMLResponse)
def views(request: Request, params: Annotated[api.ViewQueryParams, Depends()], con: DbConnectionDep):
    views = api.get_views(params, con)

    return templates.TemplateResponse(
        request=request, name="views.html", context={"views": views, "params": params})
