"""
Unit and integration tests for ScamShield AI Scam Investigation Agent.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from taskflow.tools.scam_tools import (
    extract_scam_entities,
    analyze_url_threat,
    match_scam_signatures,
    compute_scam_risk_score,
    generate_scam_report,
)
from taskflow.agents.scam_shield import ScamShieldAgent
from taskflow.server.app import app

client = TestClient(app)

SAMPLE_UPI_SCAM_TEXT = (
    "URGENT: Your electricity power will be disconnected tonight at 9:30 PM due to unpaid bill of Rs 4,850. "
    "To avoid immediate disconnection, update your details and pay via UPI to mahavitaran.desk@okaxis "
    "or call Electricity Officer Sharma at +91-9876543210 immediately. "
    "Click here to verify: http://bit.ly/bijli-bill-update"
)

SAMPLE_JOB_SCAM_TEXT = (
    "Part-time job offer! Earn Rs 3,000 to Rs 8,000 daily by liking YouTube videos and rating hotels on Google Maps. "
    "No qualification required. Daily payout to your bank or UPI. Contact Telegram HR @GlobalTalentRecruit now."
)

SAMPLE_CLEAN_TEXT = (
    "Hi Barnav, just checking in to see if you are free for coffee this Saturday afternoon at Starbucks? "
    "Let me know what time works best for you!"
)


# ============================================================================
# Tool-Level Unit Tests
# ============================================================================

def test_extract_scam_entities():
    entities = extract_scam_entities(SAMPLE_UPI_SCAM_TEXT)
    assert "upi_ids" in entities
    assert "mahavitaran.desk@okaxis" in entities["upi_ids"]
    assert len(entities["phone_numbers"]) > 0
    assert len(entities["urls"]) > 0
    assert "http://bit.ly/bijli-bill-update" in entities["urls"]
    assert len(entities["amounts"]) > 0
    assert entities["urgency_detected"] is True
    assert entities["urgency_count"] >= 1


def test_analyze_url_threat_phishing():
    threat = analyze_url_threat("http://bit.ly/bijli-bill-update")
    assert threat["is_suspicious"] is True
    assert threat["risk_score"] > 20
    assert any("shortener" in f.lower() for f in threat["flags"])


def test_analyze_url_threat_clean():
    threat = analyze_url_threat("https://www.google.com/search?q=taskflow")
    assert threat["risk_score"] <= 10
    assert threat["is_suspicious"] is False


def test_match_scam_signatures_electricity():
    matched = match_scam_signatures(SAMPLE_UPI_SCAM_TEXT)
    matched_ids = [s["id"] for s in matched]
    assert any("electricity" in mid or "upi" in mid for mid in matched_ids)


def test_match_scam_signatures_job():
    matched = match_scam_signatures(SAMPLE_JOB_SCAM_TEXT)
    matched_ids = [s["id"] for s in matched]
    assert any("job" in mid or "telegram" in mid for mid in matched_ids)


def test_compute_scam_risk_score_high():
    entities = extract_scam_entities(SAMPLE_UPI_SCAM_TEXT)
    url_threats = [analyze_url_threat(u) for u in entities["urls"]]
    matched_signatures = match_scam_signatures(SAMPLE_UPI_SCAM_TEXT)

    assessment = compute_scam_risk_score(
        entities=entities,
        matched_signatures=matched_signatures,
        url_threats=url_threats,
        raw_text=SAMPLE_UPI_SCAM_TEXT,
    )

    assert assessment["risk_score"] >= 60
    assert assessment["risk_level"] in ("HIGH", "CRITICAL", "HIGH RISK", "CRITICAL RISK")
    assert assessment["is_scam"] is True
    assert any("1930" in action for action in assessment["safety_actions"])
    assert any("cybercrime.gov.in" in action for action in assessment["safety_actions"])


def test_compute_scam_risk_score_clean():
    entities = extract_scam_entities(SAMPLE_CLEAN_TEXT)
    assessment = compute_scam_risk_score(
        entities=entities,
        matched_signatures=[],
        url_threats=[],
        raw_text=SAMPLE_CLEAN_TEXT,
    )
    assert assessment["risk_score"] < 40
    assert assessment["risk_level"] in ("LOW", "SAFE", "LOW RISK / LIKELY SAFE")
    assert assessment["is_scam"] is False


def test_generate_scam_report():
    entities = extract_scam_entities(SAMPLE_UPI_SCAM_TEXT)
    url_threats = [analyze_url_threat(u) for u in entities["urls"]]
    matched_signatures = match_scam_signatures(SAMPLE_UPI_SCAM_TEXT)
    assessment = compute_scam_risk_score(
        entities=entities,
        matched_signatures=matched_signatures,
        url_threats=url_threats,
        raw_text=SAMPLE_UPI_SCAM_TEXT,
    )

    result = generate_scam_report(
        assessment=assessment,
        entities=entities,
        matched_signatures=matched_signatures,
        url_threats=url_threats,
        investigation_summary="Simulated test summary of scam findings.",
    )

    assert "markdown_path" in result
    assert "html_path" in result
    assert Path(result["markdown_path"]).exists()
    assert Path(result["html_path"]).exists()

    md_content = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "ScamShield" in md_content
    assert "1930" in md_content


# ============================================================================
# Agent-Level Tests
# ============================================================================

def test_scam_shield_agent_direct():
    agent = ScamShieldAgent()
    res = agent.investigate(text=SAMPLE_UPI_SCAM_TEXT)

    assert res["success"] is True
    assert "risk_score" in res
    assert res["risk_score"] >= 60
    assert "evidence_chain" in res
    assert len(res["evidence_chain"]) > 0
    assert "safety_actions" in res
    assert len(res["safety_actions"]) > 0
    assert "markdown_report" in res
    assert "html_report" in res


def test_scam_shield_agent_preset_sample():
    agent = ScamShieldAgent()
    res = agent.investigate(sample_id="telegram_job")

    assert res["success"] is True
    assert res["risk_score"] >= 60
    assert "job" in res["summary"].lower() or "telegram" in res["summary"].lower() or "scam" in res["summary"].lower()


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================

def test_api_scam_samples_endpoint():
    resp = client.get("/api/scam/samples")
    assert resp.status_code == 200
    data = resp.json()
    assert "samples" in data
    assert len(data["samples"]) >= 4
    sample_ids = [s["id"] for s in data["samples"]]
    assert "upi_refund" in sample_ids
    assert "telegram_job" in sample_ids
    assert "electricity_cut" in sample_ids
    assert "fedex_customs" in sample_ids


def test_api_run_scam_shield_endpoint():
    resp = client.post("/api/run/scam-shield", json={"text": SAMPLE_UPI_SCAM_TEXT})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "risk_score" in data
    assert data["risk_score"] >= 60
    assert "markdown_report" in data
    assert "html_report" in data


def test_api_chat_routes_to_scam_shield():
    resp = client.post("/api/chat", json={
        "query": "Is this message a scam? You received Rs 25,000 refund, click bit.ly/claim-refund",
        "target_agent": "auto"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["type"] == "scamshield"
