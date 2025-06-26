FROM python:3.13-slim

RUN pip install fastapi jinja2 uvicorn smbprotocol pytest httpx
COPY ./app /app/app
COPY ./db/schema.sql /app/db/schema.sql
COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
CMD ["docker-entrypoint.sh"]
