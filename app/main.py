from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.dependencies import build_container
from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if getattr(app.state, "container", None) is None:
        app.state.container = build_container()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


def create_app(*, container: Any | None = None) -> FastAPI:
    app = FastAPI(title="Event Intelligence API", version="1.0.0", lifespan=lifespan)
    if container is not None:
        app.state.container = container
    app.include_router(api_router)
    return app


app = create_app()
