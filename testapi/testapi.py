import requests
import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, auth
import edcb
import re

smb_server = os.environ['smb_server']
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY")
FIREBASE_UID = "rec"
SERVICE_ACCOUNT_PATH = os.environ.get("SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")

# --- Firebase Admin 初期化 ---
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred)

app = FastAPI()

def get_id_token_for_user(uid: str) -> str:
    custom_token = auth.create_custom_token(uid)
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"
    res = requests.post(url, json={
        "token": custom_token.decode(),
        "returnSecureToken": True
    })
    res.raise_for_status()
    return res.json()["idToken"]

async def testapi(method: str, rec_id: int, at: datetime, file_size: int | None = None):
    cmd = edcb.CtrlCmdUtil()
    print(os.environ['EDCB_SERVER'], int(os.environ['EDCB_PORT']))
    cmd.setNWSetting(os.environ['EDCB_SERVER'], int(os.environ['EDCB_PORT']))
    info = await cmd.sendGetRecInfo(rec_id)
    if info is None:
        print('Failed to communicate with EpgTimerSrv', flush=True)
        sys.exit(1)
    elif len(info['rec_file_path']) <= 0:
        print('視聴なので何もしない', flush=True)
        return

    # ジャンル情報の抽出（見つからない場合はNone）
    genre_match = re.search(r"ジャンル\s*:\s*([^\n\r]+)", info.get("program_info", ""))
    genre = genre_match.group(1) if genre_match else None

    if method == "rec":
        url = f"{os.environ["MYTVLOG_SERVER"]}:{os.environ["MYTVLOG_PORT"]}/api/recordings"
        data = {
            'program': {
                'event_id': info['eid'],
                'service_id': info['sid'],
                'name': info['title'],
                'start_time': info['start_time_epg'].isoformat(),
                'duration': info['duration_sec'],
                'genre': genre,
            },
            'file_path': f"{smb_server}{info['rec_file_path']}",
            'file_size': file_size,
            'created_at': at.isoformat(),
        }
    elif method == "view":
        url = f"{os.environ["MYTVLOG_SERVER"]}:{os.environ["MYTVLOG_PORT"]}/api/views"
        data = {
            'program': {
                'event_id': info['eid'],
                'service_id': info['sid'],
                'name': info['title'],
                'start_time': info['start_time_epg'].isoformat(),
                'duration': info['duration_sec'],
                'genre': genre,
                'created_at': at.isoformat(),
            },
            'viewed_time': info['start_time_epg'].isoformat(),
            'created_at': at.isoformat(),
        }

    print(json.dumps(data, ensure_ascii=False), flush=True)
    id_token = get_id_token_for_user(FIREBASE_UID)

    try:
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json"
            },
            json=data,
            timeout=60)
        res.raise_for_status()
    except Exception as e:
        print(f"Remote post error: {type(e).__name__}: {e}", flush=True)

if __name__ == "__main__":
    method = sys.argv[1]
    rec_id = int(sys.argv[2])
    at = datetime.now(timezone.utc)
    file_size = int(sys.argv[3])
    asyncio.run(testapi(method, rec_id, at, file_size))
