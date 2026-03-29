"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Build and configure the ASGI application."""
    application = FastAPI(
        title="Vectra",
        description="Enterprise AI Knowledge Platform (MVP)",
        version="0.1.0",
    )
    application.include_router(health_router)
    return application


app = create_app()
