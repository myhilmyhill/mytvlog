FROM python:3.13-slim

RUN pip install fastapi jinja2 uvicorn smbprotocol pytest httpx

CMD ["docker-entrypoint.sh"]
