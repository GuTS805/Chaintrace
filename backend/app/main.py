"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import attribution, cases, graph, health, report
from app.config import get_settings
from app.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
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
    )
    app.include_router(health.router)
    app.include_router(graph.router)
    app.include_router(attribution.router)
    app.include_router(cases.router)
    app.include_router(report.router)
    return app


app = create_app()
