"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import attribution, auth, cases, graph, health, investigations, live, report, vasps
from app.config import get_settings
from app.logging import configure_logging
from app.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    if settings.env == "production" and settings.uses_default_jwt_secret:
        # Fail loudly at startup rather than silently booting with a secret
        # anyone can read from this file on GitHub — a comment telling an
        # operator to change it is not enforcement.
        raise RuntimeError(
            "JWT_SECRET is still the default demo value in a production "
            "environment (ENV=production). Set a real JWT_SECRET before "
            "starting the app."
        )
    app = FastAPI(
        title="VASP Attribution & Investigation Platform",
        version=__version__,
        description="Attribute unknown wallets to VASPs with a calibrated "
        "confidence score and a traceable evidence chain.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # The frontend reads the PDF filename off this header (fetch-based
        # download, since a plain <a href> can't carry the Bearer token);
        # browsers hide response headers from JS in CORS responses unless
        # explicitly exposed here.
        expose_headers=["Content-Disposition"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    # Added last so it's outermost — rejects an oversized request before any
    # other middleware or routing does any work on it.
    app.add_middleware(
        BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(graph.router)
    app.include_router(attribution.router)
    app.include_router(cases.router)
    app.include_router(report.router)
    app.include_router(live.router)
    app.include_router(investigations.router)
    app.include_router(vasps.router)
    return app


app = create_app()
