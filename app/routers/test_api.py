import pytest
from ..conftest import con, client, smb

def test_get_program(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.get("/api/programs/1")
    assert response.status_code == 200
    program = response.json()
    assert program["id"] == 1
    assert program["event_id"] == 11
    assert program["service_id"] == 101
    assert program["name"] == "Test Program"
    assert program["start_time"] == "2025-05-12T12:00:00+09:00"
    assert program["end_time"] == "2025-05-12T12:30:00+09:00"
    assert program["duration"] == 1800
    assert program["text"] == "Text"
    assert program["ext_text"] == "Ext Text"
    assert program["created_at"] == "2025-05-12T12:01:00+09:00"

def test_create_view(con, client):
    response = client.post("/api/viewes", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:05:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["event_id"] == 11
    assert program["service_id"] == 101
    assert program["name"] == "Test Program"
    assert program["start_time"] == "2025-05-12T12:00:00+09:00"
    assert program["duration"] == 1800
    assert program["text"] == "Text"
    assert program["ext_text"] == "Ext Text"
    assert program["created_at"] == "2025-05-12T12:05:00+09:00"

def test_create_view_延長でdurationが延びる(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.post("/api/viewes", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1860,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:05:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["duration"] == 1860

def test_create_view_延長でdurationが縮む(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.post("/api/viewes", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1740,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:05:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["duration"] == 1740

def test_create_view_created_atより前のviewed_timeでdurationが変化しても古い値で上書きしない(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
    """)
    response = client.post("/api/viewes", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1860,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "viewed_time": "2025-05-12T12:00:00+09:00",
    })
    assert response.status_code == 200
    program = client.get("/api/programs/1").json()
    assert program["duration"] == 1800

#def 延長追従

#def プログラム予約でevent_id=65535を登録するとき、同じservice_idとstart_timeの番組があればそれを優先する

#def プログラム予約でevent_id=65535が存在するとき、同じservice_idとstart_timeの番組でevent_idを上書きする


def test_get_recording(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//server/recorded/test1_2', unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings/1")
    assert response1.status_code == 200
    assert response1.json() == {
        "id": 1,
        "file_path": "//server/recorded/test1",
        "file_folder": "recorded",
        "watched_at": "2025-05-12T13:00:00+09:00",
        "deleted_at": None,
        "created_at": "2025-05-12T12:30:00+09:00",
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
            "created_at": "2025-05-12T12:01:00+09:00",
        }
    }

    response2 = client.get("/api/recordings/2")
    assert response2.status_code == 200
    assert response2.json() == {
        "id": 2,
        "file_path": "//server/recorded/test1_2",
        "file_folder": "recorded",
        "watched_at": "2025-05-12T13:00:00+09:00",
        "deleted_at": None,
        "created_at": "2025-05-12T12:30:00+09:00",
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
            "created_at": "2025-05-12T12:01:00+09:00",
        },
    }

def test_get_recordings(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//server/recorded/test1_2', unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings")
    assert response1.status_code == 200
    assert response1.json() == [{
        "id": 1,
        "file_path": "//server/recorded/test1",
        "file_folder": "recorded",
        "watched_at": "2025-05-12T13:00:00+09:00",
        "deleted_at": None,
        "created_at": "2025-05-12T12:30:00+09:00",
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
            "created_at": "2025-05-12T12:01:00+09:00",
        }
    },
    {
        "id": 2,
        "file_path": "//server/recorded/test1_2",
        "file_folder": "recorded",
        "watched_at": "2025-05-12T13:00:00+09:00",
        "deleted_at": None,
        "created_at": "2025-05-12T12:30:00+09:00",
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
            "created_at": "2025-05-12T12:01:00+09:00",
        },
    }]

def test_get_recordings_from(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T00:00:00+09:00'), 1800, unixepoch('2025-05-12T00:01:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-13T00:00:00+09:00'), 1800, unixepoch('2025-05-13T00:01:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 2, '//server/recorded/test2', NULL, NULL, unixepoch('2025-05-13T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings?from_=2025-05-13")
    assert response1.status_code == 200
    recordings1 = response1.json()
    assert len(recordings1) == 1
    assert recordings1[0]["id"] == 2

    response2 = client.get("/api/recordings?from_=2025-05-12")
    assert response2.status_code == 200
    recordings2 = response2.json()
    assert len(recordings2) == 2

def test_get_recordings_to(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T00:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-12T23:31:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 2, '//server/recorded/test2', NULL, NULL, unixepoch('2025-05-13T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings?to=2025-05-12")
    assert response1.status_code == 200
    recordings1 = response1.json()
    assert len(recordings1) == 1
    assert recordings1[0]["id"] == 1

    response2 = client.get("/api/recordings?to=2025-05-13")
    assert response2.status_code == 200
    recordings2 = response2.json()
    assert len(recordings2) == 2

def test_get_recordings_watched(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-13T12:00:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 2, '//server/recorded/test2', NULL, NULL, unixepoch('2025-05-13T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings?watched=false")
    assert response1.status_code == 200
    recordings1 = response1.json()
    assert len(recordings1) == 1
    assert recordings1[0]["id"] == 2

    response2 = client.get("/api/recordings?watched=true")
    assert response2.status_code == 200
    recordings2 = response2.json()
    assert len(recordings2) == 2

def test_get_recordings_deleted(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-13T12:00:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', NULL, unixepoch('2025-05-12T13:10:00+09:00'), unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 2, '//server/recorded/test2', NULL, NULL, unixepoch('2025-05-13T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings?deleted=false")
    assert response1.status_code == 200
    recordings1 = response1.json()
    assert len(recordings1) == 1
    assert recordings1[0]["id"] == 2

    response2 = client.get("/api/recordings?deleted=true")
    assert response2.status_code == 200
    recordings2 = response2.json()
    assert len(recordings2) == 2

def test_create_recording(con, client):
    response = client.post("/api/recordings", json={
        "program": {
            "event_id": 11,
            "service_id": 101,
            "name": "Test Program",
            "start_time": "2025-05-12T12:00:00+09:00",
            "duration": 1800,
            "text": "Text",
            "ext_text": "Ext Text",
        },
        "file_path": "//server/recorded/test1",
        "created_at": "2025-05-12T12:30:00+09:00",
    })
    assert response.status_code == 200
    recording = response.json()
    assert recording["file_path"] == "//server/recorded/test1"
    assert recording["file_folder"] == "recorded"
    assert recording["watched_at"] == None
    assert recording["deleted_at"] == None
    assert recording["created_at"] == "2025-05-12T12:30:00+09:00"
    assert recording["program"]["id"] == 1
    assert recording["program"]["event_id"] == 11
    assert recording["program"]["service_id"] == 101
    assert recording["program"]["name"] == "Test Program"
    assert recording["program"]["start_time"] == "2025-05-12T12:00:00+09:00"
    assert recording["program"]["duration"] == 1800
    assert recording["program"]["text"] == "Text"
    assert recording["program"]["ext_text"] == "Ext Text"
    assert recording["program"]["created_at"] == "2025-05-12T12:30:00+09:00"

def test_patch_recording_set_watched(con, client, smb):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'));
    """)

    response = client.patch("/api/recordings/1", json={
        "watched_at": "2025-05-12T13:00:00+09:00",
        "file_folder": "archives",
    })
    assert response.status_code == 202
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == "//server/archives/test1"
    assert recording["file_folder"] == "archives"
    assert recording["watched_at"] == "2025-05-12T13:00:00+09:00"
    assert recording["deleted_at"] == None

    smb.move_files_by_root.assert_called_with("//server/recorded/test1*", "archives")

def test_patch_recording_unset_watched(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/archives/test1', unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'));
    """)

    response = client.patch("/api/recordings/1", json={
        "watched_at": None,
    })
    assert response.status_code == 200
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == "//server/archives/test1"
    assert recording["file_folder"] == "archives"
    assert recording["watched_at"] == None
    assert recording["deleted_at"] == None

def test_patch_recording_set_deleted(con, client, smb):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/archives/test1', unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'));
    """)

    response = client.patch("/api/recordings/1", json={
        "deleted_at": "2025-05-12T13:10:00+09:00",
    })
    assert response.status_code == 202
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == ""
    assert recording["file_folder"] == None
    assert recording["watched_at"] == "2025-05-12T13:00:00+09:00"
    assert recording["deleted_at"] == "2025-05-12T13:10:00+09:00"

    smb.delete_files.assert_called_with("//server/archives/test1*")

def test_patch_recording_unset_deleted(con, client):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '', unixepoch('2025-05-12T13:00:00+09:00'), unixepoch('2025-05-12T13:10:00+09:00'), unixepoch('2025-05-12T12:30:00+09:00'));
    """)

    response = client.patch("/api/recordings/1", json={
        "deleted_at": None,
    })
    assert response.status_code == 200
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == ""
    assert recording["file_folder"] == None
    assert recording["watched_at"] == "2025-05-12T13:00:00+09:00"
    assert recording["deleted_at"] == None

def test_patch_recording_change_file_path(con, client, smb):
    con.executescript("""
        INSERT INTO programs (id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'));
        INSERT INTO recordings (id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'));
    """)

    response = client.patch("/api/recordings/1", json={
        "file_path": "//server/recorded2/test",
    })
    assert response.status_code == 200
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == "//server/recorded2/test"
    assert recording["file_folder"] == "recorded2"

    smb.move_files_by_root.assert_not_called()
