"""Single-workspace authentication and bounded HTTP request handling."""

import base64
from collections import OrderedDict, deque
import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid
from urllib.parse import urlparse
from starlette.exceptions import HTTPException

COOKIE = "driftlab_session"


def issue_session(settings):
    payload = f"{int(time.time())}.{secrets.token_urlsafe(24)}"
    signature = hmac.new(
        settings.api_key.get_secret_value().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}.{signature}".encode()).decode()


def valid_session(value, settings):
    if not settings.api_key or not value:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value.encode()).decode()
        stamp, nonce, signature = decoded.split(".")
        age = time.time() - int(stamp)
        expected = hmac.new(
            settings.api_key.get_secret_value().encode(),
            f"{stamp}.{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return 0 <= age <= settings.session_seconds and hmac.compare_digest(signature, expected)
    except (ValueError, UnicodeError):
        return False


def authenticated(request, settings):
    if not settings.api_key:
        return settings.mode == "local"
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer ") and hmac.compare_digest(
        authorization[7:].encode(), settings.api_key.get_secret_value().encode()
    ):
        return True
    return valid_session(request.cookies.get(COOKIE), settings)


class BodyTooLarge(HTTPException):
    def __init__(self):
        super().__init__(413, "Request body exceeds configured limit")


class SecurityMiddleware:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings
        self.windows = OrderedDict()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        from starlette.requests import Request

        request = Request(scope)
        begin = time.monotonic()
        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        settings = self.settings
        headers = [
            (b"x-request-id", request_id.encode()),
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"referrer-policy", b"no-referrer"),
            (b"cache-control", b"no-store"),
            (
                b"content-security-policy",
                b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'",
            ),
        ]
        if settings.mode == "server":
            headers.append((b"strict-transport-security", b"max-age=31536000"))

        async def respond(status, detail, extra=None):
            body = json.dumps({"detail": detail, "request_id": request_id}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": headers + [(b"content-type", b"application/json")] + (extra or []),
                }
            )
            await send({"type": "http.response.body", "body": body})

        host = urlparse("//" + request.headers.get("host", "")).hostname or ""
        if host not in [h.strip("[]") for h in settings.allowed_hosts]:
            return await respond(400, "Untrusted Host header")
        if (
            settings.mode == "local"
            and not settings.api_key
            and request.client
            and request.client.host not in ("127.0.0.1", "::1")
        ):
            return await respond(403, "Remote access requires authenticated server mode")
        path = request.url.path
        if "db_url" in request.query_params or "output" in request.query_params:
            return await respond(422, "Infrastructure parameters are operator-controlled")
        api_path = path[4:] if path.startswith("/api/") else path
        public = api_path in ("/livez", "/auth/session", "/auth/login", "/") or path.startswith(
            "/app"
        )
        # The root health response reveals no workspace data.
        if not public and not authenticated(request, settings):
            return await respond(401, "Authentication required", [(b"www-authenticate", b"Bearer")])
        origin = request.headers.get("origin")
        own_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin and origin not in settings.allowed_origins and origin != own_origin:
            return await respond(403, "Origin is not allowed")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return await respond(415, "Content-Type must be application/json")
            try:
                if int(request.headers.get("content-length", "0")) > settings.max_body_bytes:
                    return await respond(413, "Request body exceeds configured limit")
            except ValueError:
                return await respond(400, "Invalid Content-Length")
        if api_path not in ("/livez", "/") and not path.startswith("/app"):
            key = (
                (request.client.host if request.client else "unknown"),
                "login" if api_path == "/auth/login" else "api",
            )
            now = time.monotonic()
            window = self.windows.setdefault(key, deque())
            self.windows.move_to_end(key)
            while window and window[0] < now - 60:
                window.popleft()
            limit = 10 if key[1] == "login" else settings.requests_per_minute
            if len(window) >= limit:
                return await respond(429, "Rate limit exceeded", [(b"retry-after", b"60")])
            window.append(now)
            while len(self.windows) > 10000:
                self.windows.popitem(last=False)
        total = 0
        started = False
        status = 500

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > settings.max_body_bytes:
                    raise BodyTooLarge()
            return message

        async def secure_send(message):
            nonlocal started, status
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                message["headers"] = list(message.get("headers", [])) + headers
            await send(message)

        try:
            await self.app(scope, limited_receive, secure_send)
        except BodyTooLarge:
            if not started:
                await respond(413, "Request body exceeds configured limit")
        finally:
            logging.getLogger("driftlab.http").info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status": status,
                    "duration_ms": round((time.monotonic() - begin) * 1000, 2),
                },
            )
