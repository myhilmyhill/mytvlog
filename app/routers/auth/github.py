import os
import secrets
import hashlib
import base64
import httpx
from datetime import timedelta
from fastapi import APIRouter, Request, Response, HTTPException
from starlette.responses import RedirectResponse, HTMLResponse
from firebase_admin import auth

router = APIRouter(prefix="/auth/github", tags=["oauth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
# 開発環境などでhttpを使う場合はsecure=Falseにするなどの調整が必要だが、
# 基本的に本番はhttps前提。ローカル開発でもlocalhostはsecure cookieが使える場合が多い。
# ここでは環境変数で制御できるようにするか、デフォルトTrueにする。
SECURE_COOKIE = os.getenv("SECURE_COOKIE", "True").lower() == "true"

def create_code_verifier():
    return secrets.token_urlsafe(32)

def create_code_challenge(verifier: str):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")

@router.get("/login")
async def github_login():
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID is not set")

    # PKCE Verifier & Challenge
    verifier = create_code_verifier()
    challenge = create_code_challenge(verifier)
    
    # CSRF State
    state = secrets.token_urlsafe(16)

    # GitHub Authorize URL
    # scopeはuser:emailがあれば十分
    redirect_uri = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=user:email&state={state}&code_challenge={challenge}&code_challenge_method=S256"
    
    res = RedirectResponse(url=redirect_uri)
    
    # Cookieに保存 (VerifierとState)
    # 10分間有効
    res.set_cookie(key="oauth_verifier", value=verifier, httponly=True, secure=SECURE_COOKIE, max_age=600)
    res.set_cookie(key="oauth_state", value=state, httponly=True, secure=SECURE_COOKIE, max_age=600)
    
    return res

@router.get("/callback")
async def github_callback(request: Request, code: str, state: str):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub credentials not set")

    # CookieからVerifierとStateを取得
    verifier = request.cookies.get("oauth_verifier")
    saved_state = request.cookies.get("oauth_state")

    if not verifier or not saved_state:
        raise HTTPException(status_code=400, detail="Session expired or invalid")
    
    if state != saved_state:
        raise HTTPException(status_code=400, detail="Invalid state")

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
    
    # Firebase Custom Token Minting
    # GitHubのUIDを使ってFirebaseのUIDとする (例: github:{uid})
    firebase_uid = f"github:{github_uid}"
    
    additional_claims = {}
    if email:
        additional_claims["email"] = email

    custom_token = auth.create_custom_token(firebase_uid, additional_claims)
    if isinstance(custom_token, bytes):
        custom_token = custom_token.decode("utf-8")
    
    # Exchange Custom Token for ID Token
    api_key = os.environ.get("IDENTITY_PLATFORM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="IDENTITY_PLATFORM_API_KEY is not set")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}",
            json={"token": custom_token, "returnSecureToken": True}
        )
    
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to sign in with custom token: {res.text}")
    
    id_token = res.json().get("idToken")
    
    # Create Session Cookie
    expires_in = timedelta(days=7)
    try:
        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to create session cookie: {e}")

    # Redirect to digestions
    response = RedirectResponse(url="/digestions")
    response.set_cookie(
        key="session",
        value=session_cookie,
        max_age=int(expires_in.total_seconds()),
        httponly=True,
        secure=SECURE_COOKIE,
        samesite="Lax"
    )
    
    # Clean up OAuth cookies
    response.delete_cookie("oauth_verifier")
    response.delete_cookie("oauth_state")
    
    return response
