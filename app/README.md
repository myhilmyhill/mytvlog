$ gcloud projects get-iam-policy <project_id> --flatten="bindings[].members" --filter="bindings.members:<***.iam.gserviceaccount.com>" --format="table(bindings.role)"
ROLE
roles/bigquery.dataEditor
roles/bigquery.user
roles/firebase.admin
