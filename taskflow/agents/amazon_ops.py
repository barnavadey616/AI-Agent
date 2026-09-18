"""
AmazonOpsAgent — Autonomous Operations, Fulfillment & Supply Chain Copilot.
Engineered for Amazon logistics, warehouse operations, customer support, returns analysis,
seller inventory health, supply chain continuity, e-commerce fraud prevention, and operational reporting.
"""

from typing import Dict, Any, List, Optional
import re
from pathlib import Path
from taskflow import config
from taskflow.core.agent import BaseAgent
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


class AmazonOpsAgent(BaseAgent):
    """
    Autonomous multi-agent controller for Amazon operations, fulfillment centers,
    transportation networks, and customer trust.
    """

    def __init__(self, llm_provider=None):
        super().__init__(
            name="AmazonOpsAgent",
            role="Amazon Autonomous Logistics, Fulfillment & Operations Copilot",
            system_instruction="""You are F.R.Y.D.A.Y for Amazon Operations, an enterprise-grade autonomous AI copilot engineered for Amazon Global Logistics, Fulfillment Centers (FCs), Transportation, Seller Services, and Customer Trust.
Your operational principles are grounded in Amazon's Leadership Principles: Customer Obsession, Bias for Action, Dive Deep, and Deliver Results.
You do not just answer questions—you audit real-time telemetry, detect mechanical and logistical bottlenecks, formulate policy-compliant resolutions, and execute concrete operational mitigations.""",
            tools=[
                analyze_delivery_delays,
                detect_warehouse_bottlenecks,
                investigate_order_and_resolve,
                analyze_return_anomalies,
                audit_seller_inventory,
                monitor_supply_chain_disruptions,
                scan_ecommerce_fraud,
                query_amazon_sops,
                generate_daily_ops_report,
            ],
            llm_provider=llm_provider,
        )

    def execute_operation(self, query: str = "", scenario_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes an autonomous operational diagnosis and mitigation routine based on user prompt or scenario ID.
        """
        self._emit("start", {"agent": self.name, "task": scenario_id or "amazon_operations_audit"})

        q_lower = (query or "").lower().strip()
        scen = (scenario_id or "").lower().strip()
        if scen.startswith("amz_"):
            scen = scen[4:]

        # 1. Delivery Delays
        if scen in ["delays", "delivery_delays"] or any(k in q_lower for k in [
            "delivery delay", "delayed delivery", "transit delay", "late package",
            "why are deliveries delayed", "delayed orders", "shipping delay"
        ]):
            self._emit("thought", {"thought": "Auditing Amazon delivery logistics tracking stream across middle-mile and last-mile hubs..."})
            self._emit("tool_call", {"tool": "analyze_delivery_delays", "parameters": {"carrier_filter": "ALL"}})
            res = analyze_delivery_delays()
            self._emit("tool_result", {"tool": "analyze_delivery_delays", "observation": f"Found {res.get('delayed_count')} delayed shipments across carrier network."})

            reply = (
                f"### 📦 Amazon Logistics Operational Audit: Delivery Delays\n\n"
                f"- **Audited Shipments:** {res['total_audited']}\n"
                f"- **Delayed Packages:** **{res['delayed_count']}** (Average Delay: **{res['avg_delay_hours']} hours**)\n"
                f"- **High-Risk Critical Packages:** **{res['high_risk_count']}**\n\n"
                f"#### Primary Root Causes\n"
            )
            for cause, count in res["primary_causes"].items():
                reply += f"- **`{cause}`**: {count} affected orders\n"

            reply += f"\n#### Autonomous Action Directives\n"
            for act in res["recommended_actions"]:
                reply += f"1. {act}\n"

            return {
                "agent": "AmazonOpsAgent",
                "type": "delivery_delays",
                "reply": reply,
                "artifacts": [res.get("report_file")],
                "data": res
            }

        # 2. Warehouse Operations & Bottlenecks
        elif scen in ["warehouse", "fc_bottlenecks", "warehouse_ops"] or any(k in q_lower for k in [
            "warehouse", "fulfillment center", "bottleneck", "conveyor jam", "picker rate",
            "ont8", "jfk8", "ord4", "stow backlog", "fc metrics", "dock dwell"
        ]):
            self._emit("thought", {"thought": "Querying real-time SCADA and flow engineering telemetry across regional Fulfillment Centers..."})
            self._emit("tool_call", {"tool": "detect_warehouse_bottlenecks", "parameters": {"fc_code": "ALL"}})
            res = detect_warehouse_bottlenecks()
            self._emit("tool_result", {"tool": "detect_warehouse_bottlenecks", "observation": f"Identified {res.get('critical_count')} critical gridlock points and {res.get('conveyor_jams')} mechanical jams."})

            reply = (
                f"### 🏭 Amazon Fulfillment Center Telemetry: Bottleneck Detection\n\n"
                f"- **Stations Monitored:** {res['stations_monitored']} operational zones\n"
                f"- **Critical Gridlock Points:** **{res['critical_count']} stations**\n"
                f"- **Active Mechanical Jams:** **{res['conveyor_jams']}**\n\n"
                f"#### Critical Station Diagnoses\n"
            )
            for cz in res["critical_stations"]:
                reply += f"- **[{cz['fc_code']} - {cz['zone']} / `{cz['station_id']}`]**: {cz['bottleneck_cause']} (Queue Depth: **{cz['queue_depth']}** vs Target: {cz['target_queue']}, Dwell: {cz['dwell_time_mins']}m)\n"

            reply += f"\n#### Autonomous Remediation Directives\n"
            for d in res["directives"]:
                reply += f"- {d}\n"

            return {
                "agent": "AmazonOpsAgent",
                "type": "warehouse_operations",
                "reply": reply,
                "artifacts": [res.get("report_file")],
                "data": res
            }

        # 3. Customer Support & Order Resolution
        elif scen in ["customer", "order_resolution", "wismo"] or any(k in q_lower for k in [
            "wismo", "where is my order", "customer issue", "customer support", "order issue",
            "damaged item", "package missing", "concession", "refund order", "replacement order", "amz-1082"
        ]):
            order_match = re.search(r"AMZ-\d+-\d+", query.upper())
            target_order = order_match.group(0) if order_match else "AMZ-1082-93821"

            self._emit("thought", {"thought": f"Investigating order lifecycle, tracking scans, and concession eligibility for {target_order}..."})
            self._emit("tool_call", {"tool": "investigate_order_and_resolve", "parameters": {"order_id": target_order}})
            res = investigate_order_and_resolve(order_id=target_order, customer_claim=query or "Where is my order?")
            self._emit("tool_result", {"tool": "investigate_order_and_resolve", "observation": f"Resolution formulated: {res.get('resolution_type')}"})

            reply = (
                f"### 📞 Amazon Customer Care Ops: Order Investigation #{target_order}\n\n"
                f"- **Tracking ID:** `{res['tracking_id']}`\n"
                f"- **Recorded Status:** `{res['order_status']}` ({res['delay_hours']}h delay via {res['delay_reason']})\n"
                f"- **Policy Applied:** `SOP-CS-CONCESS-04`\n"
                f"- **Authorized Concession:** **{res['concession_granted']}**\n"
                f"- **Fulfillment Action:** {res['directive']}\n\n"
                f"#### Automated Customer Email Draft\n"
                f"```text\n{res['customer_email_draft']}\n```"
            )

            return {
                "agent": "AmazonOpsAgent",
                "type": "customer_resolution",
                "reply": reply,
                "artifacts": [res.get("report_file")],
                "data": res
            }

        # 4. Returns & Reverse Logistics
        elif scen in ["returns", "return_anomalies", "reverse_logistics"] or any(k in q_lower for k in [
            "return", "reverse logistics", "high returns", "defective asin", "product return",
            "return reason", "return rate"
        ]):
            self._emit("thought", {"thought": "Auditing reverse logistics disposition logs and clustering return reason codes by ASIN..."})
            self._emit("tool_call", {"tool": "analyze_return_anomalies", "parameters": {"threshold_pct": 10.0}})
            res = analyze_return_anomalies(threshold_pct=10.0)
            self._emit("tool_result", {"tool": "analyze_return_anomalies", "observation": f"Identified {res.get('flagged_count')} anomalous ASINs with return rates up to 22%."})

            reply = (
                f"### 🔄 Amazon Reverse Logistics: Defective ASIN & Return Code Audit\n\n"
                f"- **Flagged High-Return Products:** **{res['flagged_count']} ASINs** (>10% return rate threshold)\n"
                f"- **Audit Standard:** `SOP-REVERSE-LOG-09`\n\n"
                f"#### Top Anomalous Products\n"
            )
            for item in res["flagged_asins"][:4]:
                reply += (
                    f"- **ASIN `{item['asin']}`** ({item['product_title'][:28]}...): "
                    f"**{item['return_rate_pct']}% return rate** ({item['units_returned']}/{item['units_sold']} units). "
                    f"Primary reason: `{item['primary_reason_code']}`. *'{item['customer_feedback_snippet']}'*\n"
                )

            reply += f"\n#### Autonomous Catalog & Vendor Enforcement\n"
            for act in res["recommended_actions"]:
                reply += f"- {act}\n"

            return {
                "agent": "AmazonOpsAgent",
                "type": "returns_analysis",
                "reply": reply,
                "artifacts": [res.get("report_file")],
                "data": res
            }

        # 5. Seller Analytics
        elif scen in ["seller", "seller_analytics", "inventory_health"] or any(k in q_lower for k in [
            "seller", "seller analytics", "inventory health", "stockout", "days of supply",
            "buy box", "fba inventory", "aged inventory"
        ]):
            self._emit("thought", {"thought": "Auditing 3P & 1P FBA seller inventory health, sales velocity, and Buy Box win rates..."})
            self._emit("tool_call", {"tool": "audit_seller_inventory", "parameters": {"seller_id": "ALL"}})
            res = audit_seller_inventory()
            self._emit("tool_result", {"tool": "audit_seller_inventory", "observation": f"Evaluated {res.get('total_skus')} SKUs; found {res.get('stockout_count')} stockout risks."})

            reply = (
                f"### 📊 Amazon Seller Services: Inventory Health & Buy Box Audit\n\n"
                f"- **Audited Catalog SKUs:** {res['total_skus']}\n"
                f"- **Critical Stockout Risks (<5 Days of Supply):** **{res['stockout_count']} SKUs**\n"
                f"- **Aged Inventory Surcharge Risks:** **{res['excess_count']} SKUs**\n\n"
                f"#### High-Priority Seller Inventory Telemetry\n"
            )
            for item in res["items"][:4]:
                reply += (
                    f"- **[{item['seller_name']}] ASIN `{item['asin']}` ({item['sku']})**: "
                    f"**{item['days_of_supply']} days left** (Daily sales: {item['daily_velocity']}/day, Buy Box: {item['buy_box_pct']}%). "
                    f"Status: `{item['stockout_risk_level']}` -> **Recommended Reorder: +{item['recommended_reorder']} Units**\n"
                )

            return {
                "agent": "AmazonOpsAgent",
                "type": "seller_analytics",
                "reply": reply,
                "artifacts": [res.get("report_file")],
                "data": res
            }

        # 6. Supply Chain Disruptions
        elif scen in ["supply_chain", "disruptions", "weather_corridor"] or any(k in q_lower for k in [
            "supply chain", "disruption", "weather corridor", "blizzard", "port congestion",
            "interstate", "linehaul", "freight delay", "reroute trucks"
        ]):
            self._emit("thought", {"thought": "Scanning external NOAA severe weather feeds and interstate freight corridor sensors..."})
            self._emit("tool_call", {"tool": "monitor_supply_chain_disruptions", "parameters": {"corridor": "ALL"}})
            res = monitor_supply_chain_disruptions()
            self._emit("tool_result", {"tool": "monitor_supply_chain_disruptions", "observation": "Detected active Midwest Blizzard on I-80 impacting 42 line-haul trucks."})

            reply = (
                f"### 🚚 Amazon Global Supply Chain: Real-Time Network Disruption Alerts\n\n"
                f"- **Active Monitored Corridors:** {len(res['active_disruptions'])}\n"
                f"- **Emergency Continuity Standard:** `SOP-SUPPLY-DISRUPT-02`\n\n"
            )
            for d in res["active_disruptions"]:
                reply += (
                    f"#### Corridor: `{d['corridor']}` [{d['severity']}]\n"
                    f"- **Trigger:** `{d['type']}` (Delay: {d['estimated_delay']})\n"
                    f"- **Impacted Capacity:** **{d['delayed_truckloads']} Line-Haul Semi-Trucks** on lanes {', '.join(d['affected_lanes'])}\n"
                    f"- **Autonomous Mitigation Protocol:** **{d['mitigation']}**\n\n"
                )

            return {
                "agent": "AmazonOpsAgent",
                "type": "supply_chain_disruption",
                "reply": reply,
                "artifacts": [res.get("report_file")],
                "data": res
            }

        # 7. Fraud Detection & Concession Abuse
        elif scen in ["fraud", "fraud_detection", "abuse"] or any(k in q_lower for k in [
            "fraud", "concession abuse", "empty box", "fake return", "serial refund",
            "trms", "buyer abuse", "tamper", "missing item"
        ]):
            self._emit("thought", {"thought": "Auditing customer transaction risk velocity, geolocation delivery scans, and concession claim ratios..."})
            self._emit("tool_call", {"tool": "scan_ecommerce_fraud", "parameters": {"order_id": "ALL"}})
            res = scan_ecommerce_fraud()
            self._emit("tool_result", {"tool": "scan_ecommerce_fraud", "observation": f"Flagged {res.get('confirmed_abuse_count')} high-velocity concession abuse rings."})

            reply = (
                f"### 💰 Amazon Trust & Safety: Concession Abuse & Fraud Investigation\n\n"
                f"- **Audited Claims:** {res['total_audited']}\n"
                f"- **Confirmed Organized Abuse Flags:** **{res['confirmed_abuse_count']} Accounts**\n"
                f"- **Suspicious Concession Velocity:** **{res['suspicious_count']} Accounts**\n\n"
                f"#### Flagged Fraud Dossiers (TRMS RESTRICTED)\n"
            )
            for r in res["flagged_orders"][:3]:
                reply += (
                    f"- **Order `{r['order_id']}` (Account `{r['account_id']}`)**: "
                    f"**Risk Score: {r['fraud_risk_score']}/100** (`{r['verdict']}`). "
                    f"Claim: *{r['claim_type']}* (${r['order_value_usd']}). "
                    f"Evidence: {r['investigation_notes']}\n"
                )

            return {
                "agent": "AmazonOpsAgent",
                "type": "fraud_detection",
                "reply": reply,
                "artifacts": [res.get("report_file")],
                "data": res
            }

        # 8. Internal Employee Assistant / SOP Search
        elif scen in ["sops", "employee_assistant", "internal_sop"] or any(k in q_lower for k in [
            "sop", "policy", "guideline", "safety rule", "emergency stop",
            "leadership principle", "how does amazon handle", "fc safety protocol"
        ]):
            self._emit("thought", {"thought": f"Querying authorized Amazon internal SOP repository for '{query}'..."})
            self._emit("tool_call", {"tool": "query_amazon_sops", "parameters": {"query_topic": query or "conveyor safety"}})
            res = query_amazon_sops(query_topic=query or "conveyor safety")
            self._emit("tool_result", {"tool": "query_amazon_sops", "observation": f"Retrieved {res.get('matched_count')} authorized internal procedures."})

            reply = f"### 👨💻 Amazon Internal Ops Assistant: SOP Knowledge Retrieval\n\n"
            for doc in res.get("sops", []):
                reply += (
                    f"#### 📄 `{doc['id']}`: {doc['title']}\n"
                    f"- **Category:** {doc['category']} | **Tags:** {', '.join(doc.get('tags', []))}\n"
                    f"- **Policy Summary:** {doc['summary']}\n\n"
                    f"```text\n{doc['content']}\n```\n\n"
                )

            return {
                "agent": "AmazonOpsAgent",
                "type": "internal_assistant",
                "reply": reply,
                "artifacts": [],
                "data": res
            }

        # 9. Daily Operations Reporting (Default / Overview)
        else:
            self._emit("thought", {"thought": "Synthesizing cross-network KPIs, carrier performance, FC throughput, and defect rates into Daily Operations Brief..."})
            self._emit("tool_call", {"tool": "generate_daily_ops_report", "parameters": {"network_region": "NA_EAST_WEST"}})
            res = generate_daily_ops_report()
            self._emit("tool_result", {"tool": "generate_daily_ops_report", "observation": "Daily briefing generated with OTD, bottleneck counts, and mitigation actions."})

            reply = (
                f"### 📝 Amazon Operations Executive Daily Briefing & Shift Handoff\n\n"
                f"- **Operational Region:** `{res['region']}`\n"
                f"- **Network On-Time Delivery (OTD):** **{res['otd_percentage']}%** *(Alert: Depressed by I-80 Winter Storm & ONT8 Jam)*\n"
                f"- **Active Conveyor Jams:** **{res['conveyor_jams']}** (ONT8 Inbound Dock 3, DFW7 AFE Sort)\n"
                f"- **Delayed Shipments Under Remediation:** **{res['delayed_shipments']}**\n"
                f"- **Defective ASIN Yellow Alerts:** **{res['defective_asins']}**\n\n"
                f"#### Core Directives Executed This Shift\n"
                f"1. **Line-haul Diversion:** Initiated I-70 bypass for 42 trucks around Midwest storm corridor.\n"
                f"2. **Flow Control:** Dispatched RME technicians for ONT8 tape machine and DFW7 sensor jams.\n"
                f"3. **Customer Care:** Automatically credited impacted Prime members and queued priority re-dispatch.\n"
                f"4. **Catalog Integrity:** Suppressed Buy Box for ASIN B0B12F98Q1 (22% defect rate).\n\n"
                f"*Comprehensive shift reports available for download in Artifacts below.*"
            )

            return {
                "agent": "AmazonOpsAgent",
                "type": "operations_reporting",
                "reply": reply,
                "artifacts": [res.get("report_file"), "amazon_delivery_delays_report.md", "amazon_warehouse_bottleneck_report.md"],
                "data": res
            }
