"""
Unit tests for the four specialized automation agents.
"""

from pathlib import Path
import tempfile
import shutil
import pytest

from taskflow.agents.file_organizer import FileOrganizerAgent
from taskflow.agents.research_agent import ResearchAgent
from taskflow.agents.data_cleaner import DataCleanerAgent
from taskflow.agents.email_triage import EmailTriageAgent
from taskflow import config

def test_file_organizer_agent():
    # Setup temporary source and target directories
    with tempfile.TemporaryDirectory() as tmp_src, tempfile.TemporaryDirectory() as tmp_tgt:
        test_file = Path(tmp_src) / "test_invoice_acme.txt"
        test_file.write_text("Vendor: Acme Corp\nTotal USD: $120.00\nPayment Terms: Net 30", encoding="utf-8")

        agent = FileOrganizerAgent()
        res = agent.organize_directory(source_dir=tmp_src, target_dir=tmp_tgt)

        assert res["success"] is True
        assert res["total_processed"] == 1
        assert len(res["records"]) == 1
        assert res["records"][0]["category"] == "Invoices"

        # Check file moved
        invoices_folder = Path(tmp_tgt) / "Invoices"
        assert invoices_folder.exists()
        assert len(list(invoices_folder.glob("*"))) == 1

def test_research_agent():
    agent = ResearchAgent()
    res = agent.research(topic="Enterprise AI Automation")
    assert "topic" in res
    assert res["topic"] == "Enterprise AI Automation"
    assert "markdown_report" in res
    assert "html_report" in res
    assert res["sources_analyzed"] > 0

def test_data_cleaner_agent():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("ID,Product,Quantity,Price\n1,Widget,5,10.0\n1,Widget,5,10.0\n2,Gadget,-3,\n3,,2,15.0\n")
        temp_csv = f.name

    try:
        agent = DataCleanerAgent()
        res = agent.clean_and_analyze(file_path=temp_csv)
        assert res["success"] is True
        assert res["changes"]["duplicates_removed"] == 1
        assert res["changes"]["final_rows"] == 3
        assert res["changes"]["outliers_adjusted"] == 1
        assert Path(res["cleaned_file"]).exists()
    finally:
        if Path(temp_csv).exists():
            Path(temp_csv).unlink()

def test_email_triage_agent():
    agent = EmailTriageAgent()
    sample = [
        {"sender": "client@example.com", "subject": "URGENT: Service is down", "body": "We cannot log in!"},
        {"sender": "sales@partner.com", "subject": "Partnership inquiry", "body": "Let's explore an integration."}
    ]
    res = agent.triage_inquiries(sample)
    assert res["total_processed"] == 2
    assert res["high_urgency_count"] == 1
    assert len(res["items"]) == 2
    assert res["items"][0]["urgency"] == "High"
    assert res["items"][1]["category"] == "Partnerships"
