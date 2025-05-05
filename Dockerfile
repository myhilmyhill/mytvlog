FROM python:3.12-slim

RUN pip install fastapi jinja2 uvicorn python-multipart

CMD ["docker-entrypoint.sh"]
