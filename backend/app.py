"""
FastAPI application factory and modular app instance for TaskFlow AI.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from taskflow import config
from backend.services.background import watcher, scheduler
from backend.services.websocket import ws_router
from backend.routes import (
    system_router,
    agents_router,
    chat_router,
    knowledge_router,
    artifacts_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and graceful shutdown."""
    config.ensure_directories()
    # Register default periodic jobs
    scheduler.add_job(
        name="Hourly Data Health Audit",
        interval_seconds=3600,
        task_func=lambda: None,
        description="Periodically checks data files in outputs/cleaned_data",
    )
    scheduler.start(daemon=True)
    yield
    if watcher.is_running:
        watcher.stop()
    if scheduler.is_running:
        scheduler.stop()


def create_app() -> FastAPI:
    """Create and configure the TaskFlow AI FastAPI application."""
    app = FastAPI(
        title="TaskFlow AI Server",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(ws_router)
    app.include_router(system_router)
    app.include_router(agents_router)
    app.include_router(chat_router)
    app.include_router(knowledge_router)
    app.include_router(artifacts_router)

    # Mount static assets
    static_dir = config.BASE_DIR / "taskflow" / "server" / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
