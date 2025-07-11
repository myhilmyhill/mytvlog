from fastapi import Request
from starlette.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
import firebase_admin
from firebase_admin import auth

if not firebase_admin._apps:
    firebase_admin.initialize_app()

class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/", "/favicon.ico"]:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return HTMLResponse(status_code=404)

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            decoded_token = auth.verify_id_token(token)
            request.state.user = decoded_token
            return await call_next(request)
        except Exception as e:
            print("🔥 Firebase認証失敗:", e)
            return HTMLResponse(status_code=404, content="Invalid token\n")
