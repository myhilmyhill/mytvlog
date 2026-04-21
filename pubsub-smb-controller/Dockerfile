FROM python:3.13-slim

RUN pip install google-cloud-pubsub smbprotocol
WORKDIR /app
COPY main.py .
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN useradd -m appuser
USER appuser
CMD ["python", "main.py"]
