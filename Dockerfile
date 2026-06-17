# syntax=docker/dockerfile:1.4

######## 共通ステージ ########
FROM python:3.14-slim AS base

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

RUN pip install \
    fastapi "fastapi[standard]" jinja2 uvicorn pytest httpx itsdangerous PyJWT \
    google-cloud-bigquery google-cloud-pubsub

WORKDIR /code

COPY ./app /code/app
COPY ./db/sqlite/schemas.sql /code/db/sqlite/schemas.sql
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# ######## devステージ（compose用） ########
FROM base AS dev
USER appuser

# ######## Cloud Run用（デフォルトステージ） ########
FROM python:3.14-slim AS final

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

COPY --from=base --chown=appuser:appuser /code /code
COPY --from=base /usr/local/lib /usr/local/lib
COPY --from=base /usr/local/bin /usr/local/bin

WORKDIR /code
USER appuser
CMD ["sh", "-c", "exec fastapi run app/main.py --port $PORT"]


