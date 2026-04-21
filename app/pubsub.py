import os
import json
from google.cloud import pubsub_v1

PROJECT_ID = os.getenv("bigquery_project_id")
TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID")

publisher = None
topic_path = None

if TOPIC_ID:
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
    except Exception as e:
        print(f"Failed to initialize PubSub publisher: {e}")

def publish_to_pubsub(data: dict):
    if not topic_path or not publisher:
        print("PUBSUB_TOPIC_ID is not set. Skipping PubSub publishing.")
        return
    message_data = json.dumps(data).encode("utf-8")
    try:
        future = publisher.publish(topic_path, data=message_data)
        return future
    except Exception as e:
        print(f"Failed to publish to PubSub: {e}")
