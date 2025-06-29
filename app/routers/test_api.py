import pytest

INVALID_FILE_PATHS = [
    "/server/repo/not_double_slash_start",
    "///server/repo/too_many_slash",
    "//server//missing_repo_name",
    "//server/repo_no_trailing",
    "no_slash_prefix/server/repo",
    "//onlyserver",
    "not_full_path",
]

def test_get_program(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO views(program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T13:05:00+09:00'))
          , (1, unixepoch('2025-05-12T12:10:00+09:00'), unixepoch('2025-05-12T13:10:00+09:00'))
        ;
    """)
    response = client.get("/api/programs/1")
    assert response.status_code == 200
    assert response.json() == {
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
        "viewed_times": ["2025-05-12T12:05:00+09:00", "2025-05-12T12:10:00+09:00"],
    }

def test_get_programs(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-12T12:30:00+09:00'), 3600, 'Text 2', 'Ext Text 2', unixepoch('2025-05-12T13:31:00+09:00'))
        ;
        INSERT INTO views(program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T13:05:00+09:00'))
          , (1, unixepoch('2025-05-12T12:10:00+09:00'), unixepoch('2025-05-12T13:10:00+09:00'))
        ;
    """)
    response1 = client.get("/api/programs")
    assert response1.status_code == 200
    assert response1.json() == [{
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
        "viewed_times": [],
    },
    {
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
        "viewed_times": ["2025-05-12T12:05:00+09:00", "2025-05-12T12:10:00+09:00"],
    }]

    response2 = client.get("/api/programs?page=1&size=1")
    assert response2.status_code == 200
    assert response2.json() == [{
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
        "viewed_times": [],
    }]

    response3 = client.get("/api/programs?page=2&size=1")
    assert response3.status_code == 200
    assert response3.json() == [{
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
        "viewed_times": ["2025-05-12T12:05:00+09:00", "2025-05-12T12:10:00+09:00"],
    }]

    response4 = client.get("/api/programs?page=3&size=1")
    assert response4.status_code == 200
    assert response4.json() == []

def test_get_programs_from(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T00:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-13T00:00:00+09:00'), 3600, unixepoch('2025-05-12T13:31:00+09:00'))
        ;
    """)
    response1 = client.get("/api/programs?from_=2025-05-12")
    assert response1.status_code == 200
    programs1 = response1.json()
    assert len(programs1) == 2

    response2 = client.get("/api/programs?from_=2025-05-13")
    assert response2.status_code == 200
    programs2 = response2.json()
    assert len(programs2) == 1
    assert programs2[0]["id"] == 2

def test_get_programs_to(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T00:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-12T23:31:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
    """)
    response1 = client.get("/api/programs?to=2025-05-12")
    assert response1.status_code == 200
    programs1 = response1.json()
    assert len(programs1) == 1
    assert programs1[0]["id"] == 1

    response2 = client.get("/api/programs?to=2025-05-13")
    assert response2.status_code == 200
    programs2 = response2.json()
    assert len(programs2) == 2

def test_get_programs_search_name(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'))
          , (2, 12, 102, 'テスト番組2', unixepoch('2025-05-12T12:30:00+09:00'), 3600, 'Text 2', 'Ext Text 2', unixepoch('2025-05-12T13:31:00+09:00'))
        ;
    """)
    response1 = client.get("/api/programs?name=test")
    assert response1.status_code == 200
    programs1 = response1.json()
    assert len(programs1) == 1
    assert programs1[0]["id"] == 1

    response2 = client.get("/api/programs?name=テスト")
    assert response2.status_code == 200
    programs2 = response2.json()
    assert len(programs2) == 1
    assert programs2[0]["id"] == 2

def test_get_views_search_program_id(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-12T12:30:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO views(program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T14:05:00+09:00'))
          , (1, unixepoch('2025-05-12T12:10:00+09:00'), unixepoch('2025-05-12T14:10:00+09:00'))
          , (2, unixepoch('2025-05-12T12:35:00+09:00'), unixepoch('2025-05-12T13:35:00+09:00'))
        ;
    """)
    response = client.get("/api/views?program_id=1&page=1&size=1")    # page, size は無視される
    assert response.status_code == 200
    assert response.json() == [
        {
            "program_id": 1,
            "viewed_time": "2025-05-12T12:10:00+09:00",
            "created_at": "2025-05-12T14:10:00+09:00",
        },
        {
            "program_id": 1,
            "viewed_time": "2025-05-12T12:05:00+09:00",
            "created_at": "2025-05-12T14:05:00+09:00",
        },
    ]

def test_get_views_search_pages(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-12T12:30:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO views(program_id, viewed_time, created_at) VALUES
            (1, unixepoch('2025-05-12T12:05:00+09:00'), unixepoch('2025-05-12T14:05:00+09:00'))
          , (1, unixepoch('2025-05-12T12:10:00+09:00'), unixepoch('2025-05-12T14:10:00+09:00'))
          , (2, unixepoch('2025-05-12T12:35:00+09:00'), unixepoch('2025-05-12T13:35:00+09:00'))
        ;
    """)

    response1 = client.get("/api/views?page=1&size=2")
    assert response1.status_code == 200
    assert response1.json() == [
        {
            "program_id": 1,
            "viewed_time": "2025-05-12T12:10:00+09:00",
            "created_at": "2025-05-12T14:10:00+09:00",
        },
        {
            "program_id": 1,
            "viewed_time": "2025-05-12T12:05:00+09:00",
            "created_at": "2025-05-12T14:05:00+09:00",
        },
    ]

    response2 = client.get("/api/views?page=2&size=2")
    assert response2.status_code == 200
    assert response2.json() == [
        {
            "program_id": 2,
            "viewed_time": "2025-05-12T12:35:00+09:00",
            "created_at": "2025-05-12T13:35:00+09:00",
        },
    ]

    response3 = client.get("/api/views?page=3&size=2")
    assert response3.status_code == 200
    assert response3.json() == []

def test_create_view(con, client):
    response = client.post("/api/views", json={
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
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
    """)
    response = client.post("/api/views", json={
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
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
    """)
    response = client.post("/api/views", json={
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
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
    """)
    response = client.post("/api/views", json={
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
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', 1000000000, unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//server/recorded/test1_2', 1000000001, unixepoch('2025-05-12T13:30:00+09:00'), unixepoch('2025-05-12T14:00:00+09:00'), unixepoch('2025-05-12T12:31:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings/1")
    assert response1.status_code == 200
    assert response1.json() == {
        "id": 1,
        "file_path": "//server/recorded/test1",
        "file_folder": "recorded",
        "file_size": 1_000_000_000,
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
        "file_size": 1_000_000_001,
        "watched_at": "2025-05-12T13:30:00+09:00",
        "deleted_at": "2025-05-12T14:00:00+09:00",
        "created_at": "2025-05-12T12:31:00+09:00",
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
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, text, ext_text, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, 'Text', 'Ext Text', unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', 1000000000, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//server/recorded/test1_2', 1000000001, unixepoch('2025-05-12T13:30:00+09:00'), NULL, unixepoch('2025-05-12T12:31:00+09:00'))
          , (3, 1, '', NULL, unixepoch('2025-05-12T13:30:00+09:00'), unixepoch('2025-05-12T14:00:00+09:00'), unixepoch('2025-05-12T12:32:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings")    # 既定値は watched, deleted を除外
    assert response1.status_code == 200
    assert response1.json() == [{
        "id": 1,
        "file_path": "//server/recorded/test1",
        "file_folder": "recorded",
        "file_size": 1_000_000_000,
        "watched_at": None,
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
    }]

def test_get_recordings_search_program_id(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-12T12:30:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//server/recorded/test1_2', unixepoch('2025-05-12T12:32:00+09:00'))
          , (3, 1, '//server/recorded/test1_3', unixepoch('2025-05-12T12:31:00+09:00'))
          , (4, 2, '//server/recorded/test2', unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings?program_id=1")
    assert response1.status_code == 200
    recordings1 = response1.json()
    assert len(recordings1) == 3
    assert recordings1[0]["id"] == 1
    assert recordings1[1]["id"] == 3
    assert recordings1[2]["id"] == 2

    response2 = client.get("/api/recordings?program_id=2")
    assert response2.status_code == 200
    recordings2 = response2.json()
    assert len(recordings2) == 1
    assert recordings2[0]["id"] == 4

def test_get_recordings_search_from(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T00:00:00+09:00'), 1800, unixepoch('2025-05-12T00:01:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-13T00:00:00+09:00'), 1800, unixepoch('2025-05-13T00:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 2, '//server/recorded/test2', unixepoch('2025-05-13T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings?from_=2025-05-13")
    assert response1.status_code == 200
    recordings1 = response1.json()
    assert len(recordings1) == 1
    assert recordings1[0]["id"] == 2

    response2 = client.get("/api/recordings?from=2025-05-12")
    assert response2.status_code == 200
    recordings2 = response2.json()
    assert len(recordings2) == 2

def test_get_recordings_search_to(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T00:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-12T23:31:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 2, '//server/recorded/test2', unixepoch('2025-05-13T12:30:00+09:00'))
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

def test_get_recordings_search_watched(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-13T12:00:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
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

def test_get_recordings_search_deleted(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
          , (2, 12, 102, 'Test Program 2', unixepoch('2025-05-13T12:00:00+09:00'), 1800, unixepoch('2025-05-13T12:31:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, watched_at, deleted_at, created_at) VALUES
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

def test_get_recordings_search_file_folder(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, created_at) VALUES
            (1, 1, '//server/recorded1/test1', unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//server/recorded2/test1', unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    response1 = client.get("/api/recordings?file_folder=recorded1")
    assert response1.status_code == 200
    recordings1 = response1.json()
    assert len(recordings1) == 1
    assert recordings1[0]["id"] == 1
    response2 = client.get("/api/recordings?file_folder=recorded2")
    assert response2.status_code == 200
    recordings2 = response2.json()
    assert len(recordings2) == 1
    assert recordings2[0]["id"] == 2

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
        "file_size": 1_000_000_000,
        "created_at": "2025-05-12T12:30:00+09:00",
    })
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "file_path": "//server/recorded/test1",
        "file_size": 1_000_000_000,
        "file_folder": "recorded",
        "watched_at": None,
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
            "created_at": "2025-05-12T12:30:00+09:00",
        },
    }

@pytest.mark.parametrize("in_file_path", INVALID_FILE_PATHS)
def test_create_recordings_file_path_指定書式以外は例外(in_file_path, con, client, smb):
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
        "file_path": in_file_path,
        "file_size": 1_000_000_000,
        "created_at": "2025-05-12T12:30:00+09:00",
    })
    assert response.status_code == 400

def test_patch_recording_set_watched(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/recorded/test1', 1000000000, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
        ;
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
    assert recording["file_size"] == 1_000_000_000
    assert recording["watched_at"] == "2025-05-12T13:00:00+09:00"
    assert recording["deleted_at"] == None

    smb.move_files_by_root.assert_called_with("//server/recorded/test1*", "archives")

def test_patch_recording_unset_watched(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/archives/test1', 1000000000, unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)

    response = client.patch("/api/recordings/1", json={
        "watched_at": None,
    })
    assert response.status_code == 200
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == "//server/archives/test1"
    assert recording["file_folder"] == "archives"
    assert recording["file_size"] == 1_000_000_000
    assert recording["watched_at"] == None
    assert recording["deleted_at"] == None

def test_patch_recording_set_deleted(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//server/archives/test1', 1000000000, unixepoch('2025-05-12T13:00:00+09:00'), NULL, unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)

    response = client.patch("/api/recordings/1", json={
        "deleted_at": "2025-05-12T13:10:00+09:00",
    })
    assert response.status_code == 202
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == ""
    assert recording["file_folder"] == None
    assert recording["file_size"] == None
    assert recording["watched_at"] == "2025-05-12T13:00:00+09:00"
    assert recording["deleted_at"] == "2025-05-12T13:10:00+09:00"

    smb.delete_files.assert_called_with("//server/archives/test1*")

def test_patch_recording_unset_deleted(con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '', NULL, unixepoch('2025-05-12T13:00:00+09:00'), unixepoch('2025-05-12T13:10:00+09:00'), unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)

    response = client.patch("/api/recordings/1", json={
        "deleted_at": None,
    })
    assert response.status_code == 200
    recording = response.json()
    assert recording["id"] == 1
    assert recording["file_path"] == ""
    assert recording["file_size"] == None
    assert recording["file_folder"] == None
    assert recording["watched_at"] == "2025-05-12T13:00:00+09:00"
    assert recording["deleted_at"] == None

def test_patch_recording_change_file_path(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'))
        ;
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

@pytest.mark.parametrize("in_file_path", INVALID_FILE_PATHS)
def test_patch_recordings_change_file_path_指定書式以外は例外(in_file_path, con, client):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:01:00+09:00'))
        ;
        INSERT INTO recordings(id, program_id, file_path, created_at) VALUES
            (1, 1, '//server/recorded/test1', unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    response = client.patch("/api/recordings/1", json={
        "file_path": in_file_path,
    })
    assert response.status_code == 400
