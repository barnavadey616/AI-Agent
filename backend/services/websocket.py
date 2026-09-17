"""
WebSocket connection management and event broadcasting for TaskFlow AI.
"""

from typing import List, Any
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router = APIRouter()


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, data: Any):
        payload = json.dumps({"event": event_type, "data": data})
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


ws_manager = WebSocketManager()


async def broadcast_event(event_type: str, data: Any):
    """Asynchronously broadcast an event to all connected WebSocket clients."""
    await ws_manager.broadcast(event_type, data)


def sync_event_emitter(event_type: str, data: Any):
    """
    Bridge synchronous agent callbacks to the asynchronous WebSocket broadcaster.
    Safely schedules broadcast tasks if an asyncio loop is active.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast_event(event_type, data))
    except Exception:
        pass


@ws_router.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time ReAct logs and execution updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
