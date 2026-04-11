#!/bin/bash

docker build -t testapi .
docker run --rm \
  --env-file .env \
  -v ./serviceAccountKey.json:/app/serviceAccountKey.json \
  testapi python testapi.py $@
