def test_validate_recordings_dry_run(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//testserver/recorded/test1', 1000000001, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//testserver/recorded/no_size', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (3, 1, '//testserver/recorded/no_file', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (4, 1, '//testserver/recorded/moved_file', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (5, 1, '//testserver/recorded/moved_file2', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))

          -- deleted_at があるのに file_path が空でない
          , (6, 1, '//testserver/recorded/deleted', 1000000004, NULL, unixepoch('2025-05-12T14:00:00+09:00'), unixepoch('2025-05-12T12:30:00+09:00'))

          -- file_path が空なのに deleted_at がない
          , (7, 1, '', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))

          -- 整合
          , (8, 1, '', NULL, NULL, unixepoch('2025-05-12T14:00:00+09:00'), unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    smb.get_file_size.side_effect = lambda path: {
        "//testserver/recorded/test1": 1_000_000_001,
        "//testserver/recorded/no_size": 1_000_000_002,
        "//testserver/recorded2/moved_file": 1_000_000_003,
        "//testserver/recorded3/moved_file2": 1_000_000_004,
    }.get(path)

    response = client.post("/api/recordings/validate", json={
      "dry_run": True,
      "find_file_path_roots": ["recorded2", "recorded3"],
    })
    assert response.status_code == 200
    assert response.json() == [
        {
            "recording_id": 1,
            "file_path": "//testserver/recorded/test1",
            "found_path": "//testserver/recorded/test1",
            "file_size": 1_000_000_001,
            "exists": True,
        },
        {
            "recording_id": 2,
            "file_path": "//testserver/recorded/no_size",
            "found_path": "//testserver/recorded/no_size",
            "file_size": 1_000_000_002,
            "exists": True,
        },
        {
            "recording_id": 3,
            "file_path": "//testserver/recorded/no_file",
            "found_path": None,
            "file_size": None,
            "exists": False,
        },
        {
            "recording_id": 4,
            "file_path": "//testserver/recorded/moved_file",
            "found_path": "//testserver/recorded2/moved_file",
            "file_size": 1_000_000_003,
            "exists": True,
        },
        {
            "recording_id": 5,
            "file_path": "//testserver/recorded/moved_file2",
            "found_path": "//testserver/recorded3/moved_file2",
            "file_size": 1_000_000_004,
            "exists": True,
        },
        {
            "recording_id": 6,
            "file_path": "//testserver/recorded/deleted",
            "found_path": None,
            "file_size": None,
            "exists": False,
        },
        {
            "recording_id": 7,
            "file_path": "",
            "found_path": None,
            "file_size": None,
            "exists": False,
        },
    ]

def test_validate_recordings(con, client, smb):
    con.executescript("""
        INSERT INTO programs(id, event_id, service_id, name, start_time, duration, created_at) VALUES
            (1, 11, 101, 'Test Program', unixepoch('2025-05-12T12:00:00+09:00'), 1800, unixepoch('2025-05-12T12:31:00+09:00'))
        ;
        INSERT INTO recordings (id, program_id, file_path, file_size, watched_at, deleted_at, created_at) VALUES
            (1, 1, '//testserver/recorded/test1', 1000000001, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (2, 1, '//testserver/recorded/no_size', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (3, 1, '//testserver/recorded/no_file', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (4, 1, '//testserver/recorded/moved_file', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))
          , (5, 1, '//testserver/recorded/moved_file2', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))

          -- deleted_at があるのに file_path が空でない
          , (6, 1, '//testserver/recorded/deleted', 1000000004, NULL, unixepoch('2025-05-12T14:00:00+09:00'), unixepoch('2025-05-12T12:30:00+09:00'))

          -- file_path が空なのに deleted_at がない
          , (7, 1, '', NULL, NULL, NULL, unixepoch('2025-05-12T12:30:00+09:00'))

          -- 整合
          , (8, 1, '', NULL, NULL, unixepoch('2025-05-12T14:00:00+09:00'), unixepoch('2025-05-12T12:30:00+09:00'))
        ;
    """)
    smb.get_file_size.side_effect = lambda path: {
        "//testserver/recorded/test1": 1_000_000_001,
        "//testserver/recorded/no_size": 1_000_000_002,
        "//testserver/recorded2/moved_file": 1_000_000_003,
        "//testserver/recorded3/moved_file2": 1_000_000_004,
    }.get(path)

    response = client.post("/api/recordings/validate", json={
      "dry_run": False,
      "find_file_path_roots": ["recorded2", "recorded3"],
    })
    assert response.status_code == 200

    recording1 = client.get("/api/recordings/1").json()
    assert recording1["file_path"] == "//testserver/recorded/test1"
    assert recording1["file_size"] == 1_000_000_001

    recording2 = client.get("/api/recordings/2").json()
    assert recording2["file_path"] == "//testserver/recorded/no_size"
    assert recording2["file_size"] == 1_000_000_002

    recording3 = client.get("/api/recordings/3").json()
    assert recording3["file_path"] == ""
    assert recording3["file_size"] == None

    recording4 = client.get("/api/recordings/4").json()
    assert recording4["file_path"] == "//testserver/recorded2/moved_file"
    assert recording4["file_size"] == 1_000_000_003

    recording5 = client.get("/api/recordings/5").json()
    assert recording5["file_path"] == "//testserver/recorded3/moved_file2"
    assert recording5["file_size"] == 1_000_000_004

    recording6 = client.get("/api/recordings/6").json()
    assert recording6["file_path"] == ""
    assert recording6["file_size"] == None
    assert recording6["deleted_at"] != None

    recording7 = client.get("/api/recordings/7").json()
    assert recording7["file_path"] == ""
    assert recording7["file_size"] == None
    assert recording7["deleted_at"] != None

    recording8 = client.get("/api/recordings/8").json()
    assert recording8["file_path"] == ""
    assert recording8["file_size"] == None
    assert recording8["deleted_at"] == "2025-05-12T14:00:00+09:00"
