import os
import httpx
import time
from fastapi import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json
import base64
import jwt
from datetime import datetime, timedelta, timezone

SESSION_COOKIE_NAME = "session"
VERBOSE = os.getenv("VERBOSE", "").lower() == "true"
SECRET_KEY = os.getenv("GITHUB_CLIENT_SECRET")
# キャッシュ: {token: (user_info, expiry)}
TOKEN_CACHE = {}
CACHE_TTL = 300  # 5分
ALGORITHM = "HS256"

class GithubAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 🔓 認証スキップ対象のパス
        if path == "/" or path.startswith("/auth") or path.startswith("/static"):
            return await call_next(request)

        # ✅ 1. JWTセッションCookieで認証
        session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
        if session_cookie:
            user = self.verify_jwt(session_cookie)
            if user:
                request.state.user = user
                return await call_next(request)

        # ✅ 2. Authorizationヘッダー (Bearer) で認証
        # GitHub Token (PAT or Installation Token) を想定
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            user = await self.verify_github_token(token)
            if user:
                request.state.user = user
                return await call_next(request)

        if path.startswith("/api/"):
            return HTMLResponse(status_code=401, content="Unauthorized")

        return RedirectResponse(url="/")

    def verify_jwt(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            if VERBOSE:
                print("JWT has expired")
        except jwt.InvalidTokenError as e:
            if VERBOSE:
                print(f"JWT verification failed: {e}")
        return None

    async def verify_github_token(self, token: str):
        # キャッシュチェック
        now = time.time()
        if token in TOKEN_CACHE:
            user_info, expiry = TOKEN_CACHE[token]
            if now < expiry:
                return user_info

        # GitHub APIで検証
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if res.status_code == 200:
                    user_info = res.json()
                    # 簡易的なアクセス制限 (必要なら)
                    # if user_info.get("login") != "your-github-username": return None
                    
                    TOKEN_CACHE[token] = (user_info, now + CACHE_TTL)
                    return user_info
        except Exception as e:
            if VERBOSE:
                print(f"GitHub token verification failed: {e}")
        return None

def create_jwt(data: dict, expires_delta: timedelta = timedelta(days=7)) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
