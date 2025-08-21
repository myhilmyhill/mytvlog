# syntax=docker/dockerfile:1.4

######## 共通ステージ ########
FROM python:3.13-slim AS base

RUN pip install \
    fastapi jinja2 uvicorn smbprotocol pytest httpx \
    google-cloud-bigquery firebase-admin

COPY ./app /app/app
COPY ./db/schema.sql /app/db/schema.sql
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY ./main.py /app/main.py

WORKDIR /app

# ######## devステージ（compose用） ########
FROM base AS dev
ENTRYPOINT ["bash", "docker-entrypoint.sh"]

# ######## Cloud Run用（デフォルトステージ） ########
FROM python:3.13-slim AS final
COPY --from=base /app /app
COPY --from=base /usr/local/lib /usr/local/lib
WORKDIR /app
CMD ["python3", "main.py"]
