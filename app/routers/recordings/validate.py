from fastapi import APIRouter
from pydantic import BaseModel
from ...dependencies import DbConnectionDep, SmbDep

router = APIRouter()

class ValidateRecordings(BaseModel):
    dry_run: bool
    find_file_path_roots: list[str] = []

def find_path_with_fallbacks(
        file_path: str, find_file_path_roots: list[str], smb: SmbDep) -> tuple[str | None, int | None]:
    parts = file_path.split("/", 4)     # //server/root/to/path
    if len(parts) < 5:
        return None, None

    candidates = [f"//{parts[2]}/{r}/{parts[4]}" for r in [parts[3]] + find_file_path_roots]
    for alt_path in candidates:
        size = smb.get_file_size(alt_path)
        if size is not None:
            return alt_path, size

    return None, None

@router.post("/api/recordings/validate")
def validate_recordings(body: ValidateRecordings, con: DbConnectionDep, smb: SmbDep):
    """実ファイルとデータベースの不整合をある程度直します

       - deleted_at == NULL のとき file_path が存在しない場合、空にして deleted_at を適当に埋めます。
         find_file_path_roots で別 root （server でない）で同様のパス構造のフォルダを探します
       - deleted_at != NULL かつ file_path == '' を満たさない場合、満たすようにします
       - dry_run では変更される recordings が出力されます。
         結果的にファイルサイズが一致しても変更されるとみなします
    """
    cur = con.execute("""
        SELECT
            id AS recording_id
          , file_path
        FROM recordings
        WHERE deleted_at IS NULL OR file_path != ''
    """)

    vs = []
    for r in cur.fetchall():
        found_path, size = find_path_with_fallbacks(r["file_path"], body.find_file_path_roots, smb)
        vs.append({
            **r,
            "found_path": found_path,
            "file_size": size,
            "exists": found_path is not None
        })

    if body.dry_run:
        con.rollback()
        return vs

    con.executescript("""
        CREATE TEMP TABLE v(
            recording_id INTEGER NOT NULL
          , new_file_path TEXT
          , file_size INTEGER
        ) STRICT
        ;
    """)
    con.executemany("""
        INSERT INTO v(recording_id, new_file_path, file_size) VALUES
        (:recording_id, :found_path, :file_size)
    """, vs)
    con.execute("""
       UPDATE recordings AS r SET
           file_path = CASE
               WHEN v.file_size IS NOT NULL THEN v.new_file_path
               ELSE ''
           END
         , file_size = v.file_size
         , deleted_at = CASE WHEN v.file_size IS NULL THEN coalesce(r.deleted_at, unixepoch('now')) ELSE r.deleted_at END
       FROM v
       WHERE v.recording_id = r.id
    """)
    con.commit()

    return
