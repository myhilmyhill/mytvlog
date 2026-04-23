import time
import requests
import os
from datetime import datetime, timedelta, timezone

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REMOTE_URL = os.getenv("REMOTE_URL")
POLL_STATUS_URL = os.getenv("POLL_STATUS_URL")

def get_auth_token() -> str:
    return GITHUB_TOKEN

def post_view(url: str, id_token: str, body: dict):
    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json"
        },
        json=body,
        timeout=120)
    res.raise_for_status()

def sleep_until_next_interval(interval_minutes, delay_seconds):
    now = datetime.now(timezone.utc)
    next_minute = ((now.minute // interval_minutes) + 1) * interval_minutes
    if next_minute >= 60:
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_time = now.replace(minute=next_minute, second=0, microsecond=0)

    next_time += timedelta(seconds=delay_seconds)
    sleep_seconds = (next_time - now).total_seconds() % (interval_minutes * 60)
    if sleep_seconds > 0:
        print(f"Next run at {next_time}, sleeping for {sleep_seconds:.2f} seconds", flush=True)
        time.sleep(sleep_seconds)

def poll_once():
    print('Polling', flush=True)
    id_token = get_auth_token()
    try:
        res_status = requests.get(POLL_STATUS_URL, timeout=10)
        res_status.raise_for_status()
        status = res_status.json()
        if status.get("play_status") == "finished":
            return

        body = {
            "program": {
                "event_id": status["current_event_id"],
                "service_id": status["current_event_service_id"],
                "name": status["current_event_name"],
                "start_time": status["current_event_start_time"],
                "duration": status["current_event_duration"],
                "genre": status["current_content_nibble"],
            },
            "viewed_time": status["tot"],
            "speed": status["speed"] / 100.0 if "speed" in status else 1.0,
        }

        try:
            post_view(f"{REMOTE_URL}/api/views", id_token, body)
        except Exception as e:
            print(f"Remote post error: {type(e).__name__}: {e}", flush=True)

    except Exception as e:
        print(f"{type(e).__name__}: {e}", flush=True)

def main():
    print('Start', flush=True)
    while True:
        sleep_until_next_interval(interval_minutes=5, delay_seconds=2 * 60)
        poll_once()

if __name__ == '__main__':
    main()
