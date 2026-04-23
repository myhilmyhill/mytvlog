import requests
import asyncio
import os
import sys
import json
import smbclient
from datetime import datetime, timezone
import edcb
import re

FILE_PATH_PREFIX = os.environ['FILE_PATH_PREFIX']
SMB_USERNAME = os.getenv('SMB_USERNAME')
SMB_PASSWORD = os.getenv('SMB_PASSWORD')
EDCB_SERVER = os.environ['EDCB_SERVER']
EDCB_PORT = os.environ['EDCB_PORT']
MYTVLOG_SERVER = os.environ['MYTVLOG_SERVER']
MYTVLOG_PORT = os.environ['MYTVLOG_PORT']
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

async def testapi(method: str, rec_id: int, at: datetime):
    cmd = edcb.CtrlCmdUtil()
    cmd.setNWSetting(EDCB_SERVER, int(EDCB_PORT))
    info = await cmd.sendGetRecInfo(rec_id)
    if info is None:
        print('Failed to communicate with EpgTimerSrv')
        sys.exit(1)
    elif len(info['rec_file_path']) <= 0:
        print('視聴なので何もしない')
        return

    # ジャンル情報の抽出（見つからない場合はNone）
    genre_match = re.search(r"ジャンル\s*:\s*([^\n\r]+)", info.get("program_info", ""))
    genre = genre_match.group(1) if genre_match else None

    if method == "rec":
        # SMBアクセス用のフルパスを構築
        full_path = f"{FILE_PATH_PREFIX}{info['rec_file_path']}"
        normalized_path = full_path.replace("\\", "/")

        try:
            # サーバー名を取得（//server/share/... の形式を想定）
            if normalized_path.startswith("//"):
                server = normalized_path.split("/")[2]
                # セッションを登録（常に登録し直すか、既存のものを利用する）
                smbclient.register_session(server, username=SMB_USERNAME, password=SMB_PASSWORD)

            stat = smbclient.stat(normalized_path)
            file_size = stat.st_size
        except Exception as e:
            print(f"SMBからのファイルサイズ取得に失敗しました: {e}")
            file_size = None

        url = f"{MYTVLOG_SERVER}:{MYTVLOG_PORT}/api/recordings"
        data = {
            'program': {
                'event_id': info['eid'],
                'service_id': info['sid'],
                'name': info['title'],
                'start_time': info['start_time_epg'].isoformat(),
                'duration': info['duration_sec'],
                'genre': genre,
            },
            'file_path': normalized_path,
            'file_size': file_size,
            'created_at': at.isoformat(),
        }
    elif method == "view":
        url = f"{MYTVLOG_SERVER}:{MYTVLOG_PORT}/api/views"
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
            'speed': 1.0,
            'created_at': at.isoformat(),
        }

    print(json.dumps(data, ensure_ascii=False))

    try:
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json"
            },
            json=data,
            timeout=120)
        res.raise_for_status()
    except Exception as e:
        print(f"Remote post error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python testapi.py <method(rec|view)> <rec_id>")
        sys.exit(1)

    method = sys.argv[1]
    rec_id = int(sys.argv[2])
    at = datetime.now(timezone.utc)

    asyncio.run(testapi(method, rec_id, at))
