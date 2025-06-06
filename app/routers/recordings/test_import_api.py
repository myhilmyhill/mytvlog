from datetime import datetime
from unittest.mock import AsyncMock

def test_import_recordings_dry_run(con, client, smb):
    smb.get_file_size.side_effect = lambda path: {
        "//recorded/test1": 1_000_000_001,
        "//recorded/test2": 1_000_000_002,
    }[path]

    response = client.post("/api/recordings/import-json", json={
      "dry_run": True,
      "imports": [
        {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "text": "Text",
            "ext_text": "Ext Text",
            "file_path": "//recorded/test1",
            "created_at": "2025-05-12T12:31:00+09:00",
        },
        {
            "event_id": 12,
            "service_id": 102,
            "name": "Test Program 2",
            "start_time": "2025-05-12T12:30:00+09:00",
            "duration": 3600,
            "text": "Text 2",
            "ext_text": "Ext Text 2",
            "file_path": "//recorded/test2",
            "created_at": "2025-05-12T13:31:00+09:00",
        },
      ],
    })
    assert response.status_code == 200
    recordings = response.json()
    assert recordings["count_programs"] == 2
    assert recordings["count_recordings"] == 2
    assert recordings["preview_imports"] == [
        {
            "new_recording_id": 1,
            "temp_program_id": 1,
            "existing_program_id": None,
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "text": "Text",
            "ext_text": "Ext Text",
            "file_path": "//recorded/test1",
            "file_size": 1_000_000_001,
            "created_at": "2025-05-12T12:31:00+09:00",
        },
        {
            "new_recording_id": 2,
            "temp_program_id": 2,
            "existing_program_id": None,
            "event_id": 12,
            "service_id": 102,
            "name": "Test Program 2",
            "start_time": "2025-05-12T12:30:00+09:00",
            "duration": 3600,
            "text": "Text 2",
            "ext_text": "Ext Text 2",
            "file_path": "//recorded/test2",
            "file_size": 1_000_000_002,
            "created_at": "2025-05-12T13:31:00+09:00",
        },
    ]

def test_import_recordings(con, client, smb):
    smb.get_file_size.side_effect = lambda path: {
        "//recorded/test1": 1_000_000_001,
        "//recorded/test2": 1_000_000_002,
    }[path]

    response = client.post("/api/recordings/import-json", json={
      "dry_run": False,
      "imports": [
        {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "text": "Text",
            "ext_text": "Ext Text",
            "file_path": "//recorded/test1",
            "created_at": "2025-05-12T12:31:00+09:00",
        },
        {
            "event_id": 12,
            "service_id": 102,
            "name": "Test Program 2",
            "start_time": "2025-05-12T12:30:00+09:00",
            "duration": 3600,
            "text": "Text 2",
            "ext_text": "Ext Text 2",
            "file_path": "//recorded/test2",
            "created_at": "2025-05-12T13:31:00+09:00",
        },
      ],
    })
    assert response.status_code == 200
    assert response.json()["count_programs"] == 2
    assert response.json()["count_recordings"] == 2
    recordings = client.get("/api/recordings").json()
    def k(d): return d["id"]
    assert sorted(recordings, key=k) == sorted([
        {
            "id": 1,
            "program": {
                "id": 1,
                "event_id": 11,
                "service_id": 101,
                "name": "Test Program",
                "start_time": "2025-05-12T12:00:00+09:00",
                "duration": 1800,
                "end_time": "2025-05-12T12:30:00+09:00",
                "text": "Text",
                "ext_text": "Ext Text",
                "created_at": "2025-05-12T12:31:00+09:00",
            },
            "file_path": "//recorded/test1",
            "file_folder": "test1",
            "file_size": 1_000_000_001,
            "created_at": "2025-05-12T12:31:00+09:00",
            "watched_at": None,
            "deleted_at": None,
        },
        {
            "id": 2,
            "program": {
                "id": 2,
                "event_id": 12,
                "service_id": 102,
                "name": "Test Program 2",
                "start_time": "2025-05-12T12:30:00+09:00",
                "duration": 3600,
                "end_time": "2025-05-12T13:30:00+09:00",
                "text": "Text 2",
                "ext_text": "Ext Text 2",
                "created_at": "2025-05-12T13:31:00+09:00",
            },
            "file_path": "//recorded/test2",
            "file_folder": "test2",
            "file_size": 1_000_000_002,
            "created_at": "2025-05-12T13:31:00+09:00",
            "watched_at": None,
            "deleted_at": None,
        },
    ], key=k)

def test_import_recordings_dry_run_すでに同じprogramsがあればそれを使う(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
        ;
    """)
    smb.get_file_size.side_effect = lambda path: {
        "//recorded/test1": 1_000_000_001,
    }[path]

    response = client.post("/api/recordings/import-json", json={
      "dry_run": True,
      "imports": [
        {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "file_path": "//recorded/test1",
            "created_at": "2025-05-12T12:32:00+09:00",
        },
      ],
    })
    assert response.status_code == 200
    assert response.json()["count_programs"] == 0
    assert response.json()["count_recordings"] == 1

    recording = response.json()["preview_imports"][0]
    assert recording["new_recording_id"] == 1
    assert recording["temp_program_id"] == None
    assert recording["existing_program_id"] == 1
    assert recording["event_id"] == 11
    assert recording["service_id"] == 101
    assert recording["name"] == "Test Program"
    assert recording["start_time"] == "2025-05-12T12:00:00+09:00"
    assert recording["duration"] == 1800
    assert recording["file_path"] == "//recorded/test1"
    assert recording["created_at"] == "2025-05-12T12:32:00+09:00"

def test_import_recordings_すでに同じprogramsがあればそれを使う(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
        ;
    """)
    smb.get_file_size.side_effect = lambda path: {
        "//recorded/test1": 1_000_000_001,
    }[path]

    response = client.post("/api/recordings/import-json", json={
      "dry_run": False,
      "imports": [
        {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "file_path": "//recorded/test1",
            "created_at": "2025-05-12T12:32:00+09:00",
        },
      ],
    })
    assert response.status_code == 200
    assert response.json()["count_programs"] == 0
    assert response.json()["count_recordings"] == 1

    recording = client.get("/api/recordings/1").json()
    assert recording["id"] == 1
    assert recording["program"]["event_id"] == 11
    assert recording["program"]["service_id"] == 101
    assert recording["program"]["name"] == "Test Program"
    assert recording["program"]["start_time"] == "2025-05-12T12:00:00+09:00"
    assert recording["program"]["duration"] == 1800
    assert recording["program"]["created_at"] == "2025-05-12T12:31:00+09:00"
    assert recording["file_path"] == "//recorded/test1"
    assert recording["created_at"] == "2025-05-12T12:32:00+09:00"

def test_import_recordings_dry_run_すでに同じファイルのrecordingがあれば登録しない(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//testserver/recorded/test1', 1000000001, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    smb.get_file_size.side_effect = lambda path: {
        "//testserver/recorded/test1": 1_000_000_001,
    }[path]

    response = client.post("/api/recordings/import-json", json={
      "dry_run": True,
      "imports": [
        {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "file_path": "//testserver/recorded/test1",
            "created_at": "2025-05-12T12:32:00+09:00",
        },
      ],
    })
    assert response.status_code == 200
    assert response.json()["count_programs"] == 0
    assert response.json()["count_recordings"] == 0
    assert response.json()["preview_imports"] == []

def test_import_recordings_from_edcb(con, client, smb, edcb):
    r = [
        {
            "eid": 11,
            "sid": 101,
            "title": "Test Program",
            "start_time_epg": datetime.fromisoformat("2025-05-12T12:00:00+09:00"),
            "duration_sec": 1800,
            "rec_file_path": "/test1",
        },
        {
            "eid": 12,
            "sid": 102,
            "title": "Test Program 2",
            "start_time_epg": datetime.fromisoformat("2025-05-12T12:30:00+09:00"),
            "duration_sec": 3600,
            "rec_file_path": "/test2",
        },
    ]
    smb.get_file_size.side_effect = lambda path: {
        "//testserver/test1": 1_000_000_001,
        "//testserver/test2": 1_000_000_002,
    }[path]
    edcb.sendEnumRecInfoBasic = AsyncMock(return_value=r)

    response = client.post("/api/recordings/import-edcb", json={
        "dry_run": True,
        "smb_server": "testserver",
        "recording_created_at": "2025-05-12T12:32:00+09:00"
    })
    assert response.status_code == 200
    assert response.json()["count_edcb_recordings"] == 2
    assert response.json()["count_programs"] == 2
    assert response.json()["count_recordings"] == 2

    recordings = response.json()["preview_imports"]
    assert recordings[0]["new_recording_id"] == 1
    assert recordings[0]["temp_program_id"] == 1
    assert recordings[0]["event_id"] == 11
    assert recordings[0]["service_id"] == 101
    assert recordings[0]["name"] ==  "Test Program"
    assert recordings[0]["start_time"] == "2025-05-12T12:00:00+09:00"
    assert recordings[0]["duration"] == 1800
    assert recordings[0]["text"] == None
    assert recordings[0]["ext_text"] == None
    assert recordings[0]["file_path"] == "//testserver/test1"
    assert recordings[0]["file_size"] == 1_000_000_001
    assert recordings[0]["created_at"] == "2025-05-12T12:32:00+09:00"

    assert recordings[1]["new_recording_id"] == 2
    assert recordings[1]["temp_program_id"] == 2
    assert recordings[1]["event_id"] == 12
    assert recordings[1]["service_id"] == 102
    assert recordings[1]["name"] == "Test Program 2"
    assert recordings[1]["start_time"] == "2025-05-12T12:30:00+09:00"
    assert recordings[1]["duration"] == 3600
    assert recordings[1]["text"] == None
    assert recordings[1]["ext_text"] == None
    assert recordings[1]["file_path"] == "//testserver/test2"
    assert recordings[1]["file_size"] == 1_000_000_002
    assert recordings[1]["created_at"] == "2025-05-12T12:32:00+09:00"
