from fastapi import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import firebase_admin
from firebase_admin import credentials, auth
import os
import traceback

SESSION_COOKIE_NAME = "session"
SERVICE_ACCOUNT_KEY_PATH = "/etc/gcp/serviceAccountKey.json"
VERBOSE = os.getenv("VERBOSE", "").lower() == "true"

from ..firebase import initialize_firebase
initialize_firebase()

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
            except Exception as e:
                if VERBOSE:
                    traceback.print_exc()
                else:
                    print(f"{e.__class__.__name__}: {e}")
            else:
                return await call_next(request)

        # ✅ 2. Authorizationヘッダー (Bearer) で認証
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                decoded = auth.verify_id_token(token)
                request.state.user = decoded
            except Exception as e:
                if VERBOSE:
                    traceback.print_exc()
                else:
                    print(f"{e.__class__.__name__}: {e}")
            else:
                return await call_next(request)

        if path.startswith("/api/"):
            return HTMLResponse(status_code=401, content="Unauthorized")

        return RedirectResponse(url="/")
