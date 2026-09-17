"""
FastAPI Server for TaskFlow AI.
Provides REST APIs, WebSocket real-time agent execution streaming, and serves the Web Dashboard.
Delegates to the modular backend package while maintaining full backwards compatibility.
"""

from backend.app import app, create_app, lifespan
from backend.services.background import watcher, scheduler
from backend.services.websocket import (
    ws_manager,
    broadcast_event,
    sync_event_emitter,
)
from backend.models.schemas import (
    RunOrganizerRequest,
    RunResearchRequest,
    RunDataCleanRequest,
    RunEmailTriageRequest,
    RunCustomTaskRequest,
    NaturalTaskRequest,
    AddKnowledgeRequest,
    SearchKnowledgeRequest,
)

connected_websockets = ws_manager.active_connections

__all__ = [
    "app",
    "create_app",
    "lifespan",
    "watcher",
    "scheduler",
    "ws_manager",
    "broadcast_event",
    "sync_event_emitter",
    "connected_websockets",
    "RunOrganizerRequest",
    "RunResearchRequest",
    "RunDataCleanRequest",
    "RunEmailTriageRequest",
    "RunCustomTaskRequest",
    "NaturalTaskRequest",
    "AddKnowledgeRequest",
    "SearchKnowledgeRequest",
]
