from fastapi import Request
from starlette.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
import firebase_admin
from firebase_admin import auth

SESSION_COOKIE_NAME = "session"

if not firebase_admin._apps:
    firebase_admin.initialize_app()

class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 🔓 認証スキップ対象のパス
        if path == "/" or path.startswith("/auth"):
            return await call_next(request)

        # ✅ 1. セッションCookieで認証
        session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
        if session_cookie:
            try:
                decoded = auth.verify_session_cookie(session_cookie, check_revoked=True)
                request.state.user = decoded
                return await call_next(request)
            except Exception as e:
                print("⚠️ セッションCookie無効:", e)

        # ✅ 2. Authorizationヘッダー (Bearer) で認証
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                decoded = auth.verify_id_token(token)
                request.state.user = decoded
                return await call_next(request)
            except Exception as e:
                print("🔥 Firebase認証失敗:", e)

        return HTMLResponse(status_code=404)
