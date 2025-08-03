# syntax=docker/dockerfile:1.4

######## 共通ステージ ########
FROM python:3.13-slim AS base

RUN pip install --no-cache-dir \
    fastapi jinja2 uvicorn smbprotocol pytest httpx \
    google-cloud-bigquery firebase-admin

COPY ./app /app/app
COPY ./db/schema.sql /app/db/schema.sql
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY ./main.py /app/main.py

WORKDIR /app

######## devステージ（compose用） ########
FROM base AS dev
ENTRYPOINT ["bash", "docker-entrypoint.sh"]

######## Cloud Run用（デフォルトステージ） ########
FROM gcr.io/distroless/python3 AS final
COPY --from=base /app /app
COPY --from=base /usr/local /usr/local
WORKDIR /app
ENTRYPOINT ["python3", "main.py"]
