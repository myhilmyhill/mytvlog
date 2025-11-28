from fastapi import APIRouter, Body, Response, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import auth
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_NAME = "session"

if not firebase_admin._apps:
    firebase_admin.initialize_app()

class LoginRequest(BaseModel):
    id_token: str

@router.post("/login")
async def login(response: Response, id_token: str = Body(embed=True)):
    try:
        decoded_token = auth.verify_id_token(id_token)
        expires_in = timedelta(days=7)
        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_cookie,
            max_age=expires_in.total_seconds(),
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        return
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"認証エラー: {e}")
