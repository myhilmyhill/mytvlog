FROM python:3.14-slim

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

RUN pip install requests

WORKDIR /app
USER appuser
