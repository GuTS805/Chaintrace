"""Standalone ASGI/Starlette middleware: security response headers and a
request body size cap. Neither depends on anything else in the app, so they
can be unit-tested directly against a bare ASGI app."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers that cost nothing and matter even for a pure JSON+PDF API —
    e.g. a PDF report response with no X-Content-Type-Options could still be
    MIME-sniffed by an old browser into something it isn't."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # Meaningful only over HTTPS; harmless to set unconditionally — a
        # terminating reverse proxy decides whether HTTPS is actually in use.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class BodySizeLimitMiddleware:
    """Rejects a request whose declared Content-Length exceeds the cap before
    any handler runs. This API takes small JSON bodies only — no uploads —
    so a low cap is a pure DoS guard, not a real usage constraint."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            content_length = headers.get(b"content-length")
            if content_length is not None:
                try:
                    size = int(content_length)
                except ValueError:
                    size = 0
                if size > self.max_bytes:
                    response = PlainTextResponse(
                        f"Request body exceeds the {self.max_bytes}-byte limit.",
                        status_code=413,
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)
