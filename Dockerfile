# syntax=docker/dockerfile:1.4

######## 共通ステージ ########
FROM python:3.13-slim AS base

RUN pip install \
    fastapi jinja2 uvicorn pytest httpx \
    google-cloud-bigquery firebase-admin \
    google-genai

COPY ./app /app/app
COPY ./db/sqlite/schemas.sql /app/db/sqlite/schemas.sql
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY ./main.py /app/main.py

WORKDIR /app

# ######## devステージ（compose用） ########
FROM base AS dev

# ######## Cloud Run用（デフォルトステージ） ########
FROM python:3.13-slim AS final
COPY --from=base /app /app
COPY --from=base /usr/local/lib /usr/local/lib
WORKDIR /app
CMD ["python3", "main.py"]
