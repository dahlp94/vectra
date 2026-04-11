"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.query import router as query_router


def create_app() -> FastAPI:
    """Build and configure the ASGI application."""
    application = FastAPI(
        title="Vectra",
        description="Enterprise AI Knowledge Platform (MVP)",
        version="0.1.0",
    )
    application.include_router(health_router)
    application.include_router(ingest_router)
    application.include_router(documents_router)
    application.include_router(query_router)
    return application


app = create_app()