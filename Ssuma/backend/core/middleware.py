import hmac
import os
import time
import uuid
from typing import Dict, Set

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


PUBLIC_PATHS: Set[str] = {
    "/api/health",
    "/api/v1/health",
    "/api/version",
    "/docs",
    "/openapi.json",
    "/redoc",
}

SSE_PATHS: Set[str] = {
    "/api/v1/flow/chat/stream",
    "/api/v1/chat/stream",
}

SENSITIVE_PATHS: Set[str] = {
    "/api/cache/clear",
    "/api/v1/cache/clear",
    "/api/settings/llm",
    "/api/v1/llm/config",
    "/api/evolution/action",
    "/api/v1/evolution/action",
    "/api/orchestrator/reset",
    "/api/v1/orchestrator/reset",
}


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = None
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode()
                break
        if not request_id:
            request_id = str(uuid.uuid4())

        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_id)


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}
        self.max_ips = 10000

    def _get_client_ip(self, scope: Scope) -> str:
        for key, value in scope.get("headers", []):
            if key == b"x-forwarded-for":
                return value.decode().split(",")[0].strip()
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"

    def _clean_old_requests(self, key: str, now: float):
        if key in self.requests:
            self.requests[key] = [
                ts for ts in self.requests[key]
                if now - ts < 60
            ]
            if not self.requests[key]:
                del self.requests[key]
        if len(self.requests) > self.max_ips:
            sorted_keys = sorted(
                self.requests.keys(),
                key=lambda k: self.requests[k][-1] if self.requests[k] else 0
            )
            for k in sorted_keys[:len(self.requests) - self.max_ips]:
                del self.requests[k]

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in PUBLIC_PATHS or path in SSE_PATHS:
            await self.app(scope, receive, send)
            return

        now = time.time()
        key = self._get_client_ip(scope)
        self._clean_old_requests(key, now)

        if key not in self.requests:
            self.requests[key] = []

        if len(self.requests[key]) >= self.requests_per_minute:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )
            await response(scope, receive, send)
            return

        self.requests[key].append(now)
        await self.app(scope, receive, send)


class RequestBodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_size: int = 10 * 1024 * 1024):
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in SSE_PATHS:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        if method in ("POST", "PUT", "PATCH"):
            for key, value in scope.get("headers", []):
                if key == b"content-length":
                    if int(value) > self.max_body_size:
                        response = JSONResponse(
                            status_code=413,
                            content={"detail": f"Request body too large. Maximum size is {self.max_body_size // (1024 * 1024)}MB"}
                        )
                        await response(scope, receive, send)
                        return
                    break

        await self.app(scope, receive, send)


class APIKeyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self._api_key = os.environ.get("SSUMA_API_KEY", "")

    @property
    def api_key(self) -> str:
        if not self._api_key:
            try:
                from core.config import Config
                config = Config()
                self._api_key = config.storage.get("api_key", "")
            except Exception:
                pass
        return self._api_key

    def _extract_key(self, scope: Scope) -> str:
        for key, value in scope.get("headers", []):
            if key == b"authorization":
                decoded = value.decode()
                if decoded.startswith("Bearer "):
                    return decoded[7:]
            if key == b"x-api-key":
                return value.decode()
        return ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        if path.startswith("/ws/") or path in SSE_PATHS or path in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        key = self.api_key
        if not key:
            await self.app(scope, receive, send)
            return

        is_sensitive = any(path.startswith(p) for p in SENSITIVE_PATHS)
        provided = self._extract_key(scope)

        if is_sensitive and not hmac.compare_digest(provided, key):
            response = JSONResponse(
                status_code=401,
                content={"detail": "API key required for this endpoint"}
            )
            await response(scope, receive, send)
            return

        if not is_sensitive and provided and not hmac.compare_digest(provided, key):
            response = JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"}
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
