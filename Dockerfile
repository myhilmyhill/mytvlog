# syntax=docker/dockerfile:1.4

######## 共通ステージ ########
FROM python:3.14-slim AS base

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

RUN pip install \
    fastapi jinja2 uvicorn pytest httpx itsdangerous PyJWT \
    google-cloud-bigquery google-cloud-pubsub

WORKDIR /app

COPY ./app /app/app
COPY ./db/sqlite/schemas.sql /app/db/sqlite/schemas.sql
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY ./main.py /app/main.py

# ######## devステージ（compose用） ########
FROM base AS dev
USER appuser

# ######## Cloud Run用（デフォルトステージ） ########
FROM python:3.14-slim AS final

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

COPY --from=base --chown=appuser:appuser /app /app
COPY --from=base /usr/local/lib /usr/local/lib
COPY --from=base /usr/local/bin /usr/local/bin

WORKDIR /app
USER appuser
CMD ["python3", "main.py"]
