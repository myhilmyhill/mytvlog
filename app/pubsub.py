import os
import json

PROJECT_ID = os.getenv("bigquery_project_id")
TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID")

_publisher = None
_topic_path = None

def _get_publisher():
    global _publisher, _topic_path
    if _publisher is None and TOPIC_ID:
        from google.cloud import pubsub_v1
        
        if TOPIC_ID.endswith("-sub"):
            print(f"WARNING: PUBSUB_TOPIC_ID '{TOPIC_ID}' ends with '-sub'. "
                  "This might be a subscription ID instead of a topic ID.")
        try:
            _publisher = pubsub_v1.PublisherClient()
            _topic_path = _publisher.topic_path(PROJECT_ID, TOPIC_ID)
        except Exception as e:
            print(f"Failed to initialize PubSub publisher: {e}")
    return _publisher, _topic_path

def publish_to_pubsub(data: dict):
    publisher, topic_path = _get_publisher()
    if not topic_path or not publisher:
        print("PUBSUB_TOPIC_ID is not set. Skipping PubSub publishing.")
        return
    message_data = json.dumps(data).encode("utf-8")
    try:
        print(f"Publishing to {topic_path}: {data}")
        future = publisher.publish(topic_path, data=message_data)
        message_id = future.result()
        print(f"Published message ID: {message_id}")
        return message_id
    except Exception as e:
        print(f"Failed to publish to PubSub: {e}")

