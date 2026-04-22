FROM python:3.13-slim
RUN pip install "fastapi[standard]" requests firebase-admin smbprotocol
COPY edcb.py /app/edcb.py
COPY testapi.py /app/testapi.py
WORKDIR /app
ENV PYTHONUNBUFFERED=1
CMD ["python", "testapi.py"]
