FROM python:3.13-slim
RUN pip install "fastapi[standard]" requests firebase-admin
COPY edcb.py /app/edcb.py
COPY testapi.py /app/testapi.py
WORKDIR /app
CMD ["python", "testapi.py"]
