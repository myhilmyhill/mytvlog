import time
import urllib.request
import json
from datetime import datetime, timedelta
import sys
import os

def run_job(poll_status_url: str):
    with urllib.request.urlopen(poll_status_url, timeout=10) as res_status:
        status = json.loads(res_status.read().decode())
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
        data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request('http://mytvlog/api/viewes', data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=10) as res:
            pass

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

def main():
    print('Start', flush=True)
    while True:
        sleep_until_next_interval(interval_minutes=5, delay_seconds=2 * 60)
        print('Polling', flush=True)
        try:
            run_job(os.environ['poll_status_url'])
        except Exception as e:
            print(f"{type(e).__name__}: {e}", flush=True)

if __name__ == '__main__':
    main()
