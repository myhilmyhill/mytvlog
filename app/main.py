from typing import Annotated
from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from datetime import datetime
from .dependencies import DbConnectionDep
from .routers import api

app = FastAPI()
app.include_router(api.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def digestions(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        WITH agg_recs AS(
            SELECT
                program_id, json_group_array(id) AS rec_ids
                ,
                json_group_array(CASE WHEN watched_at IS NOT NULL THEN 1 ELSE 0 END) AS watcheds
            FROM recordings
            WHERE watched_at IS NULL AND deleted_at IS NULL
            GROUP BY program_id
        )
        , agg_views AS (
            SELECT program_id, json_group_array(viewed_time) AS views
            FROM views
            GROUP BY program_id
        )
        SELECT
            programs.id, programs.name, programs.service_id, programs.start_time, programs.duration
            ,
            programs.start_time AS "start_time_string [timestamp]"
            ,
            agg_views.views
            ,
            agg_recs.rec_ids, agg_recs.watcheds
        FROM programs
        INNER JOIN agg_recs ON agg_recs.program_id = programs.id
        LEFT OUTER JOIN agg_views ON agg_views.program_id = programs.id
        ORDER BY programs.start_time
    """)
    agg = cur.fetchall()
    rec_zip = lambda id: zip(*next([x["rec_ids"].split(","), x["watcheds"].split(",")] for x in agg if x["id"] == id))

    return templates.TemplateResponse(
        request=request, name="index.html", context={"agg": agg, "rec_zip": rec_zip})

@app.get("/programs", response_class=HTMLResponse)
def programs(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        WITH agg_views AS (
            SELECT program_id, json_group_array(viewed_time) AS views
            FROM views
            GROUP BY program_id
        )
        SELECT id, name, service_id, start_time
            ,
            start_time AS "start_time_str [timestamp]",
            start_time + duration AS "end_time_str [timestamp]",
            duration,
            created_at AS "created_at [timestamp]"
            ,
            agg_views.views
        FROM programs
        LEFT OUTER JOIN agg_views ON agg_views.program_id = programs.id
        ORDER BY start_time DESC
    """)
    programs = cur.fetchall()
    return templates.TemplateResponse(
        request=request, name="programs.html", context={"programs": programs})

@app.get("/recordings", response_class=HTMLResponse)
def recordings(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        SELECT recordings.id, program_id, file_path,
            watched_at AS "watched_at [timestamp]", deleted_at AS "deleted_at [timestamp]",
            programs.name, programs.service_id
        FROM recordings
        INNER JOIN programs ON programs.id = recordings.program_id
        ORDER BY programs.start_time DESC
    """)
    recordings = cur.fetchall()
    return templates.TemplateResponse(
        request=request, name="recordings.html", context={"recordings": recordings})

@app.get("/views", response_class=HTMLResponse)
def views(request: Request, con: DbConnectionDep):
    cur = con.cursor()

    cur.execute("""
        SELECT program_id, viewed_time AS "viewed_time [timestamp]", programs.name,
            views.created_at AS "created_at [timestamp]"
        FROM views
        INNER JOIN programs ON programs.id = views.program_id
        ORDER BY "created_at [timestamp]" DESC
    """)
    views = cur.fetchall()
    return templates.TemplateResponse(
        request=request, name="views.html", context={"views": views})
