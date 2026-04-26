#!/bin/bash

docker build -t testapi .
docker run --rm --env-file .env testapi python testapi.py $@
