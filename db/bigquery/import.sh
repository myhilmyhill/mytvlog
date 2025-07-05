#!/bin/bash

PROJECT=$bigquery_project_id
DATASET=$bigquery_dataset_id
sed "s/\${DATASET}/$DATASET/g" schemas.sql | bq query --use_legacy_sql=false --project_id=$PROJECT
if [ -f programs.csv ]; then
  bq load \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --replace \
    --project_id=$PROJECT \
    $DATASET.programs \
    programs.csv
fi
if [ -f recordings.csv ]; then
  bq load \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --replace \
    --project_id=$PROJECT \
    $DATASET.recordings \
    recordings.csv
fi
if [ -f views.csv ]; then
  bq load \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --replace \
    --project_id=$PROJECT \
    $DATASET.views \
    views.csv
fi
