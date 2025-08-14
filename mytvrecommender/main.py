from typing import Any
import httpx
from datetime import datetime, timedelta
from fastmcp import FastMCP
import edcb
import os
import firebase_admin
from firebase_admin import credentials, auth

mcp = FastMCP("mytvrecommender")
PORT = os.environ["PORT"]
MYTVLOG_API_BASE = f"http://mytvlog:{PORT}"
EDCB_SERVER = os.environ["EDCB_SERVER"]
EDCB_PORT = os.getenv("EDCB_PORT", "4510")

FIREBASE_API_KEY = os.environ["FIREBASE_API_KEY"]
FIREBASE_UID = "poll"
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH", "/etc/gcp/serviceAccountKey.json")
PORT = os.environ['PORT']
REMOTE_URL = os.environ['REMOTE_URL']

# --- Firebase Admin 初期化 ---
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred)

def get_id_token_for_user(uid: str) -> str:
    custom_token = auth.create_custom_token(uid)
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"
    res = httpx.post(url, json={
        "token": custom_token.decode(),
        "returnSecureToken": True
    })
    res.raise_for_status()
    return res.json()["idToken"]

async def make_request(url: str, id_token: str) -> dict[str, Any] | None:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {id_token}",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

# @mcp.resource("programs://viewed", mime_type="application/json")
@mcp.tool()
async def get_viewed_programs() -> list:
    """最近見た・録画した番組情報を100件取得します
    """
    id_token = get_id_token_for_user(FIREBASE_UID)
    url = f"{MYTVLOG_API_BASE}/api/programs?size=100"
    return await make_request(url, id_token)

def extract_unique_epg_info(epg_data):
    seen_keys = set()
    result = []
    for service in epg_data:
        for event in service.get("event_list", []):
            key = (
                event.get("short_info", {}).get("event_name", ""),
                event["start_time"],
                event["duration_sec"]
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            result.append({
                "onid": event["onid"],
                "tsid": event["tsid"],
                "sid": event["sid"],
                "eid": event["eid"],
                "start_time": event["start_time"],
                "duration": event["duration_sec"],
                "event_name": event.get("short_info", {}).get("event_name", "")
            })
    return result

@mcp.tool()
async def reserve_event(onid: int, tsid: int, sid: int, eid: int) -> bool:
    """録画予約します"""
    cmd = edcb.CtrlCmdUtil()
    cmd.setNWSetting(EDCB_SERVER, EDCB_PORT)
    now = datetime.now() + timedelta(hours=9)
    next_ = now + timedelta(days=1)
    events = await cmd.sendEnumPgInfoEx([
        0, onid<<32 | tsid<<16 | sid,
        edcb.EDCBUtil.datetimeToFileTime(now),
        edcb.EDCBUtil.datetimeToFileTime(next_),
    ])
    program = next(e for e in events[0]["event_list"] if e["eid"] == eid)
    r = edcb.ReserveData(
        onid=onid,
        tsid=tsid,
        sid=sid,
        eid=eid,
        rec_setting=edcb.RecSettingData(
            rec_mode=3,
            priority=1,
            tuijyuu_flag=True,
            service_mode=0,
            pittari_flag=True,
            bat_file_path='',
            rec_folder_list=[],
            suspend_mode=0,
            reboot_flag=False,
            continue_rec_flag=False,
            partial_rec_flag=0,
            tuner_id=0,
            partial_rec_folder=[]
        ),
        title=program["short_info"]["event_name"],
        start_time=(t := program["start_time"]),
        start_time_epg=t,
        duration_second=program["duration_sec"],
        station_name='',
    )
    return await cmd.sendAddReserve([r])

# @mcp.resource("events://futures", mime_type="application/json")
@mcp.tool()
async def get_future_events() -> list:
    """これから放送する番組情報を1日分取得します"""
    cmd = edcb.CtrlCmdUtil()
    cmd.setNWSetting(EDCB_SERVER, EDCB_PORT)
    now = datetime.now() + timedelta(hours=9)
    next_ = now + timedelta(days=1)
    services = await cmd.sendEnumService()
    args = []
    for s in services:
        args.append(0)
        args.append(s["onid"]<<32 | s["tsid"]<<16 | s["sid"])
    args.append(edcb.EDCBUtil.datetimeToFileTime(now))
    args.append(edcb.EDCBUtil.datetimeToFileTime(next_))
    events = await cmd.sendEnumPgInfoEx(args)
    return extract_unique_epg_info(events)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3001, path="/mcp")
    # mcp.run(transport="stdio")
