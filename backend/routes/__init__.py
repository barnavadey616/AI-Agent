from backend.routes.system import system_router
from backend.routes.agents import agents_router
from backend.routes.chat import chat_router
from backend.routes.knowledge import knowledge_router
from backend.routes.artifacts import artifacts_router

__all__ = [
    "system_router",
    "agents_router",
    "chat_router",
    "knowledge_router",
    "artifacts_router",
]
