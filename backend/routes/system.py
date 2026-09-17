"""
System and health routes for TaskFlow AI.
"""

from fastapi import APIRouter, Query
from taskflow import config
from backend.services.background import watcher, scheduler

system_router = APIRouter(tags=["System"])


@system_router.get("/api/status")
def get_status():
    """Retrieve operational status, model mode, and background services."""
    return {
        "status": "online",
        "mode": "Simulation (Heuristic Engine)" if config.IS_SIMULATION else f"Live Gemini ({config.GEMINI_MODEL})",
        "model": config.GEMINI_MODEL,
        "is_simulation": config.IS_SIMULATION,
        "watcher_active": watcher.is_running,
        "scheduler_active": scheduler.is_running,
        "watch_dir": str(config.WATCH_DIR.relative_to(config.BASE_DIR)),
        "organized_dir": str(config.ORGANIZED_DIR.relative_to(config.BASE_DIR)),
        "reports_dir": str(config.REPORTS_DIR.relative_to(config.BASE_DIR)),
        "scheduled_jobs": scheduler.list_jobs(),
    }


@system_router.post("/api/watcher/toggle")
def toggle_watcher(active: bool = Query(...)):
    """Enable or disable the real-time directory watcher."""
    if active and not watcher.is_running:
        watcher.start(daemon=True)
    elif not active and watcher.is_running:
        watcher.stop()
    return {"watcher_active": watcher.is_running}
