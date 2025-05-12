FROM python:3.12-slim

RUN pip install fastapi jinja2 uvicorn python-multipart smbprotocol pytest httpx

CMD ["docker-entrypoint.sh"]
