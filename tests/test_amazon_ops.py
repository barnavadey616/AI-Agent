"""
Comprehensive test suite for Amazon Operations & Logistics Autonomous Copilot.
Tests all 9 operational tools, AmazonOpsAgent execution, scenario APIs, and chat routing.
"""

import pytest
from fastapi.testclient import TestClient
from taskflow.server.app import app
from taskflow.agents.amazon_ops import AmazonOpsAgent
from taskflow.tools.amazon_tools import (
    analyze_delivery_delays,
    detect_warehouse_bottlenecks,
    investigate_order_and_resolve,
    analyze_return_anomalies,
    audit_seller_inventory,
    monitor_supply_chain_disruptions,
    scan_ecommerce_fraud,
    query_amazon_sops,
    generate_daily_ops_report,
)

client = TestClient(app)


def test_amazon_delivery_delays_tool():
    res = analyze_delivery_delays()
    assert res["total_audited"] > 0
    assert res["delayed_count"] > 0
    assert "SORT_JAM" in res["primary_causes"] or len(res["primary_causes"]) > 0
    assert len(res["recommended_actions"]) > 0
    assert res["report_file"].endswith(".md")


def test_amazon_warehouse_bottlenecks_tool():
    res = detect_warehouse_bottlenecks()
    assert res["stations_monitored"] > 0
    assert res["critical_count"] > 0
    assert res["conveyor_jams"] >= 1
    assert len(res["directives"]) > 0


def test_amazon_order_resolution_tool():
    res = investigate_order_and_resolve(order_id="AMZ-1082-93821", customer_claim="Package delayed")
    assert res["order_id"] == "AMZ-1082-93821"
    assert "concession_granted" in res
    assert "customer_email_draft" in res
    assert "SOP-CS-CONCESS-04" in res["policy_applied"]


def test_amazon_returns_tool():
    res = analyze_return_anomalies(threshold_pct=10.0)
    assert res["flagged_count"] > 0
    assert len(res["flagged_asins"]) > 0
    assert any(a["asin"] == "B0B12F98Q1" for a in res["flagged_asins"])


def test_amazon_seller_tool():
    res = audit_seller_inventory()
    assert res["total_skus"] > 0
    assert res["stockout_count"] > 0
    assert len(res["items"]) > 0


def test_amazon_supply_chain_tool():
    res = monitor_supply_chain_disruptions()
    assert len(res["active_disruptions"]) > 0
    first = res["active_disruptions"][0]
    assert "corridor" in first
    assert "mitigation" in first


def test_amazon_fraud_tool():
    res = scan_ecommerce_fraud()
    assert res["total_audited"] > 0
    assert res["confirmed_abuse_count"] > 0
    assert len(res["flagged_orders"]) > 0


def test_amazon_sops_tool():
    res = query_amazon_sops("conveyor jam safety")
    assert res["matched_count"] > 0
    assert any("SOP-FC-SAFE-2026" in s["id"] for s in res["sops"])


def test_amazon_daily_ops_tool():
    res = generate_daily_ops_report()
    assert res["otd_percentage"] > 0
    assert res["delayed_shipments"] > 0
    assert res["conveyor_jams"] >= 1


def test_amazon_ops_agent_execute_scenarios():
    agent = AmazonOpsAgent()
    
    # 1. Delays
    delays_res = agent.execute_operation(scenario_id="amz_delays")
    assert delays_res["agent"] == "AmazonOpsAgent"
    assert delays_res["type"] == "delivery_delays"
    assert "Delivery Delays" in delays_res["reply"]

    # 2. Warehouse
    wh_res = agent.execute_operation(scenario_id="amz_warehouse")
    assert wh_res["type"] == "warehouse_operations"
    assert "Bottleneck" in wh_res["reply"]

    # 3. Customer
    cust_res = agent.execute_operation(scenario_id="amz_customer", query="Where is my order AMZ-1082-93821?")
    assert cust_res["type"] == "customer_resolution"
    assert "AMZ-1082-93821" in cust_res["reply"]


def test_api_amazon_scenarios_endpoint():
    resp = client.get("/api/amazon/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) == 9
    ids = [s["id"] for s in data["scenarios"]]
    assert "amz_delays" in ids
    assert "amz_warehouse" in ids
    assert "amz_daily_ops" in ids


def test_api_run_amazon_ops_endpoint():
    resp = client.post("/api/run/amazon-ops", json={"scenario_id": "amz_delays", "query": "Audit delayed packages"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "AmazonOpsAgent"
    assert "reply" in data


def test_api_chat_amazon_ops_routing():
    # Explicit target agent
    resp = client.post("/api/chat", json={"query": "Check delivery delays across hubs", "target_agent": "amazon_ops"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "AmazonOpsAgent"
    assert "Delivery Delays" in data["reply"]

    # Auto-detection via sample_id
    resp_sample = client.post("/api/chat", json={"query": "Run FC bottleneck analysis", "target_agent": "auto", "sample_id": "amz_warehouse"})
    assert resp_sample.status_code == 200
    data_sample = resp_sample.json()
    assert data_sample["agent"] == "AmazonOpsAgent"
    assert data_sample["type"] == "warehouse_operations"

    # Auto-detection via natural language operational keywords
    resp_nl = client.post("/api/chat", json={"query": "Why are deliveries delayed in fulfillment centers today?", "target_agent": "auto"})
    assert resp_nl.status_code == 200
    data_nl = resp_nl.json()
    assert data_nl["agent"] == "AmazonOpsAgent"
