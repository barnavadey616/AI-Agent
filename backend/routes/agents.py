"""
Execution routes for specialized and custom TaskFlow AI agents.
"""

from fastapi import APIRouter
from taskflow import config
from taskflow.agents.file_organizer import FileOrganizerAgent
from taskflow.agents.research_agent import ResearchAgent
from taskflow.agents.data_cleaner import DataCleanerAgent
from taskflow.agents.email_triage import EmailTriageAgent
from taskflow.core.agent import BaseAgent
from backend.models.schemas import (
    RunOrganizerRequest,
    RunResearchRequest,
    RunDataCleanRequest,
    RunEmailTriageRequest,
    RunCustomTaskRequest,
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
