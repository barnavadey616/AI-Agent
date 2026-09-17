"""
Execution routes for specialized and custom TaskFlow AI agents.
"""

from fastapi import APIRouter
from taskflow import config
from taskflow.agents.file_organizer import FileOrganizerAgent
from taskflow.agents.research_agent import ResearchAgent
from taskflow.agents.data_cleaner import DataCleanerAgent
from taskflow.agents.email_triage import EmailTriageAgent
from taskflow.agents.scam_shield import ScamShieldAgent
from taskflow.core.agent import BaseAgent
from backend.models.schemas import (
    RunOrganizerRequest,
    RunResearchRequest,
    RunDataCleanRequest,
    RunEmailTriageRequest,
    RunCustomTaskRequest,
    RunScamInvestigationRequest,
)
from backend.services.websocket import sync_event_emitter

agents_router = APIRouter(tags=["Agents"])


@agents_router.post("/api/run/organizer")
def run_organizer(req: RunOrganizerRequest):
    """Execute the Document and Inbox Organizer Agent."""
    agent = FileOrganizerAgent()
    agent.add_listener(sync_event_emitter)
    src = req.source_dir or str(config.WATCH_DIR)
    tgt = req.target_dir or str(config.ORGANIZED_DIR)
    return agent.organize_directory(source_dir=src, target_dir=tgt)


@agents_router.post("/api/run/research")
def run_research(req: RunResearchRequest):
    """Execute the Autonomous Research Agent."""
    agent = ResearchAgent()
    agent.add_listener(sync_event_emitter)
    return agent.research(topic=req.topic, urls=req.urls)


@agents_router.post("/api/run/data-clean")
def run_data_clean(req: RunDataCleanRequest):
    """Execute the Data Cleaner and Anomaly Detection Agent."""
    agent = DataCleanerAgent()
    agent.add_listener(sync_event_emitter)
    target_file = req.file_path or str(config.BASE_DIR / "demo_data" / "raw_sales_dirty.csv")
    return agent.clean_and_analyze(file_path=target_file, output_path=req.output_path)


@agents_router.post("/api/run/email-triage")
def run_email_triage(req: RunEmailTriageRequest):
    """Execute the Customer and Email Inquiry Triage Agent."""
    agent = EmailTriageAgent()
    agent.add_listener(sync_event_emitter)
    inquiries = req.inquiries or [
        {
            "sender": "alex.support@enterprise.org",
            "subject": "CRITICAL: Database connection timeout on production",
            "body": "Hi, our analytics cluster is experiencing intermittent 504 errors on database queries. Please investigate right away.",
        },
        {
            "sender": "clara@investments.com",
            "subject": "Inquiry regarding Enterprise Automation License",
            "body": "Hello, we are evaluating TaskFlow AI for 200 operational seats. Can you provide enterprise security documentation and pricing?",
        },
    ]
    return agent.triage_inquiries(inquiries)


@agents_router.post("/api/run/custom")
def run_custom_task(req: RunCustomTaskRequest):
    """Execute an ad-hoc ReAct agent for custom task instructions."""
    agent = BaseAgent(
        name=req.agent_name or "GeneralTaskAgent",
        role="Autonomous Task Automation Assistant",
        system_instruction="Analyze and fulfill user instructions accurately.",
    )
    agent.add_listener(sync_event_emitter)
    result = agent.run(req.prompt)
    return result.to_dict()


@agents_router.get("/api/scam/samples")
def get_scam_samples():
    """Returns pre-loaded realistic scam samples for 1-click 'wow demo' testing."""
    samples_dir = config.BASE_DIR / "demo_data" / "scam_samples"
    samples = [
        {
            "id": "upi_refund",
            "name": "📱 Fake UPI Refund & Cashback Request",
            "category": "Financial Fraud",
            "type": "screenshot",
            "description": "PhonePe/GPay ₹25,000 refund collect request asking to enter UPI PIN to receive money.",
            "file_path": str(samples_dir / "upi_refund_scam.png"),
            "text": (samples_dir / "upi_refund_scam.txt").read_text(encoding="utf-8") if (samples_dir / "upi_refund_scam.txt").exists() else ""
        },
        {
            "id": "telegram_job",
            "name": "💼 Telegram YouTube Rating Job Scam",
            "category": "Employment Fraud",
            "type": "text",
            "description": "WhatsApp job offer promising ₹5,000/day for liking YouTube videos, escalating to prepaid merchant tasks.",
            "text": (samples_dir / "telegram_job_scam.txt").read_text(encoding="utf-8") if (samples_dir / "telegram_job_scam.txt").exists() else ""
        },
        {
            "id": "electricity_cut",
            "name": "⚡ Urgent Electricity Disconnection SMS",
            "category": "Utility Extortion",
            "type": "text",
            "description": "SMS threatening immediate power cutoff tonight at 9:30 PM with personal mobile contact number.",
            "text": (samples_dir / "electricity_cut_sms.txt").read_text(encoding="utf-8") if (samples_dir / "electricity_cut_sms.txt").exists() else ""
        },
        {
            "id": "fedex_customs",
            "name": "📦 FedEx Customs Narcotics Digital Arrest",
            "category": "Legal Impersonation",
            "type": "text",
            "description": "Impounded parcel notice claiming illegal narcotics booked with your Aadhaar, demanding clearance bond.",
            "text": (samples_dir / "fedex_customs_phish.txt").read_text(encoding="utf-8") if (samples_dir / "fedex_customs_phish.txt").exists() else ""
        }
    ]
    return {"samples": samples}


@agents_router.post("/api/run/scam-shield")
def run_scam_shield(req: RunScamInvestigationRequest):
    """Execute the ScamShield Cyber Threat & Fraud Investigation Agent."""
    agent = ScamShieldAgent()
    agent.add_listener(sync_event_emitter)

    evidence_text = req.text
    evidence_image = req.image_base64
    file_path = req.file_path

    # If sample_id is provided, load the pre-configured sample
    if req.sample_id:
        samples_dir = config.BASE_DIR / "demo_data" / "scam_samples"
        if req.sample_id == "upi_refund":
            img_p = samples_dir / "upi_refund_scam.png"
            if img_p.exists():
                file_path = str(img_p)
            txt_p = samples_dir / "upi_refund_scam.txt"
            if txt_p.exists():
                evidence_text = txt_p.read_text(encoding="utf-8")
        elif req.sample_id == "telegram_job":
            txt_p = samples_dir / "telegram_job_scam.txt"
            if txt_p.exists():
                evidence_text = txt_p.read_text(encoding="utf-8")
        elif req.sample_id == "electricity_cut":
            txt_p = samples_dir / "electricity_cut_sms.txt"
            if txt_p.exists():
                evidence_text = txt_p.read_text(encoding="utf-8")
        elif req.sample_id == "fedex_customs":
            txt_p = samples_dir / "fedex_customs_phish.txt"
            if txt_p.exists():
                evidence_text = txt_p.read_text(encoding="utf-8")

    return agent.investigate(
        text=evidence_text,
        image_base64=evidence_image,
        file_path=file_path
    )
