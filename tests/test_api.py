"""
Unit tests for FastAPI REST endpoints.
"""

from fastapi.testclient import TestClient
import pytest
from taskflow.server.app import app

client = TestClient(app)

def test_api_status():
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "model" in data
    assert "mode" in data

def test_api_artifacts_endpoint():
    resp = client.get("/api/artifacts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_api_run_research():
    resp = client.post("/api/run/research", json={"topic": "Agentic AI Automation"})
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "markdown_report" in data

def test_api_run_custom_task():
    resp = client.post("/api/run/custom", json={"prompt": "Summarize task execution."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

def test_ui_index_loads():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "TaskFlow AI" in resp.text
    assert "Task Search (ChatGPT)" in resp.text

def test_api_chat_endpoint():
    resp = client.post("/api/chat", json={"query": "Research latest agentic breakthroughs", "target_agent": "auto"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["type"] == "research"
