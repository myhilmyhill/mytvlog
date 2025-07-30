import time
import requests
import os
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth

FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY")
FIREBASE_UID = "poll"
SERVICE_ACCOUNT_PATH = os.environ.get("SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
PORT = os.environ['PORT']
REMOTE_URL = os.environ['REMOTE_URL']

# --- Firebase Admin 初期化 ---
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred)

def get_id_token_for_user(uid: str) -> str:
    custom_token = auth.create_custom_token(uid)
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"
    res = requests.post(url, json={
        "token": custom_token.decode(),
        "returnSecureToken": True
    })
    res.raise_for_status()
    return res.json()["idToken"]

def post_view(url: str, id_token: str, body: dict):
    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json"
        },
        json=body,
        timeout=10)
    res.raise_for_status()

def sleep_until_next_interval(interval_minutes, delay_seconds):
    now = datetime.now()
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
    id_token = get_id_token_for_user(FIREBASE_UID)
    try:
        res_status = requests.get(os.environ['poll_status_url'], timeout=10)
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
                "duration": status["current_event_duration"]
            },
            "viewed_time": status["tot"]
        }

        try:
            post_view(f"http://mytvlog:{PORT}/api/views", id_token, body)
        except Exception as e:
            print(f"Local post error: {type(e).__name__}: {e}", flush=True)
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
