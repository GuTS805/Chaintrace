"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.api import graph, health
from app.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="VASP Attribution & Investigation Platform",
        version=__version__,
        description="Attribute unknown wallets to VASPs with a calibrated "
        "confidence score and a traceable evidence chain.",
    )
    app.include_router(health.router)
    app.include_router(graph.router)
    return app


app = create_app()
