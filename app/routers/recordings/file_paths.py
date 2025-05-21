from fastapi import APIRouter
from ...dependencies import DbConnectionDep, SmbDep

router = APIRouter()

@router.get("/api/recordings/file-paths/validate")
def validate_file_paths(con: DbConnectionDep, smb: SmbDep):
    cur = con.execute("""
        SELECT id, program_id, file_path
        FROM recordings
        WHERE deleted_at IS NULL AND file_path LIKE '//%/%'
    """)
    return [{
        "exists": False,
        "recording": recording
    } for recording in cur.fetchall()
    if not smb.exists(recording["file_path"])]

@router.put("api/recordings/file-paths")
def rename_file_paths():
    pass
