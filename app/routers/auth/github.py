import os
import secrets
import hashlib
import base64
import httpx
import hmac
from datetime import timedelta
from fastapi import APIRouter, Request, Response, HTTPException
from starlette.responses import RedirectResponse, HTMLResponse
from ...middlewares.github_auth import create_jwt, SECRET_KEY, SESSION_COOKIE_NAME

router = APIRouter(prefix="/auth/github", tags=["oauth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

def create_code_verifier():
    return secrets.token_urlsafe(32)

def create_code_challenge(verifier: str):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")

def sign_state(state: str, verifier: str) -> str:
    """stateとverifierを署名付きでパッキングする"""
    payload = f"{state}:{verifier}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_state(signed_state: str) -> tuple[str, str]:
    """署名を検証してstateとverifierを取り出す"""
    try:
        parts = signed_state.split(":")
        if len(parts) != 3:
            return None, None
        state, verifier, signature = parts
        expected_signature = hmac.new(SECRET_KEY.encode(), f"{state}:{verifier}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return state, verifier
    except Exception:
        pass
    return None, None

@router.get("/login")
async def github_login(request: Request):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID is not set")

    verifier = create_code_verifier()
    challenge = create_code_challenge(verifier)
    csrf_state = secrets.token_urlsafe(16)
    # Cookieを使わず、stateパラメータに全て詰め込む (署名付き)
    signed_state = sign_state(csrf_state, verifier)
    redirect_uri = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=user:email&state={signed_state}&code_challenge={challenge}&code_challenge_method=S256"
    return RedirectResponse(url=redirect_uri)

@router.get("/callback")
async def github_callback(request: Request, code: str, state: str):
    print(f"DEBUG: callback called with code={code[:5]}... state={state[:10]}...")
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub credentials not set")

    # stateパラメータからverifierを復元
    saved_state, verifier = verify_state(state)

    if not verifier:
        raise HTTPException(status_code=400, detail="Invalid or tampered state")

    # Token Exchange
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "code_verifier": verifier,
            }
        )
    
    if token_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get access token")
    
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail=f"No access token: {token_data}")

    # Get User Info
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        
    if user_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")
        
    user_data = user_res.json()
    github_uid = str(user_data["id"])
    email = user_data.get("email")
    
    # Create Session JWT
    user_info = {
        "id": user_data["id"],
        "login": user_data["login"],
        "email": email,
        "firebase_uid": f"github:{github_uid}"
    }
    
    session_jwt = create_jwt(user_info)
    expires_in = timedelta(days=7)

    response = RedirectResponse(url="/digestions")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_jwt,
        max_age=int(expires_in.total_seconds()),
        httponly=True,
        secure=True,
        samesite="Lax"
    )
    
    return response
