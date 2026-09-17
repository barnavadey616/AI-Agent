"""
Unit and integration tests for the modular backend package.
"""

from fastapi.testclient import TestClient
import pytest

import backend
import backend.routes
from backend.app import app, create_app
from taskflow.server.app import app as legacy_app

client = TestClient(app)
legacy_client = TestClient(legacy_app)


def test_backend_package_imports():
    """Verify backend and its submodules are importable."""
    assert backend.__version__ == "1.0.0"
    assert hasattr(backend, "app")
    assert hasattr(backend, "create_app")
    assert hasattr(backend.routes, "system_router")
    assert hasattr(backend.routes, "agents_router")
    assert hasattr(backend.routes, "chat_router")
    assert hasattr(backend.routes, "knowledge_router")
    assert hasattr(backend.routes, "artifacts_router")


def test_backend_status_endpoint():
    """Test /api/status returns expected metadata."""
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "model" in data
    assert "watcher_active" in data
    assert "scheduler_active" in data


def test_backend_watcher_toggle():
    """Test toggling directory watcher via API."""
    # Toggle on
    resp_on = client.post("/api/watcher/toggle?active=true")
    assert resp_on.status_code == 200
    assert resp_on.json()["watcher_active"] is True

    # Toggle off
    resp_off = client.post("/api/watcher/toggle?active=false")
    assert resp_off.status_code == 200
    assert resp_off.json()["watcher_active"] is False


def test_backend_knowledge_crud():
    """Test knowledge base listing, addition, search, and deletion."""
    # 1. Add document
    add_payload = {
        "title": "Backend Architecture Policy 2026",
        "content": "Modular routing ensures isolation of system, agents, chat, knowledge, and artifacts.",
        "category": "Architecture",
        "tags": ["modular", "backend", "fastapi"]
    }
    add_resp = client.post("/api/knowledge", json=add_payload)
    assert add_resp.status_code == 200
    doc_data = add_resp.json()
    assert doc_data["success"] is True
    doc_id = doc_data["document"]["id"]

    # 2. Search document
    search_resp = client.post("/api/knowledge/search", json={"query": "modular routing", "top_k": 3})
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert any(r["id"] == doc_id for r in results)

    # 3. Delete document
    del_resp = client.delete(f"/api/knowledge/{doc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


def test_backend_artifacts_endpoint():
    """Test listing artifacts returns a valid list."""
    resp = client.get("/api/artifacts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_backend_chat_routing():
    """Test chat route natural language classification."""
    resp = client.post("/api/chat", json={"query": "Summarize automated reporting", "target_agent": "auto"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data


def test_legacy_app_backward_compatibility():
    """Verify taskflow.server.app:app works identically."""
    resp = legacy_client.get("/api/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"
