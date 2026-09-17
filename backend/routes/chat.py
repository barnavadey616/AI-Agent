"""
Chat and natural language task dispatch router for TaskFlow AI.
"""

import re
from fastapi import APIRouter
from taskflow import config
from taskflow.agents.file_organizer import FileOrganizerAgent
from taskflow.agents.research_agent import ResearchAgent
from taskflow.agents.data_cleaner import DataCleanerAgent
from taskflow.agents.email_triage import EmailTriageAgent
from taskflow.core.agent import BaseAgent
from taskflow.core.knowledge import default_knowledge_base
from taskflow.tools.file_tools import scan_directory, read_file_snippet
from taskflow.tools.web_tools import fetch_web_page, search_topics
from taskflow.tools.data_tools import profile_dataset, clean_dataset
from backend.models.schemas import NaturalTaskRequest
from backend.services.websocket import sync_event_emitter

chat_router = APIRouter(tags=["Chat"])


@chat_router.post("/api/chat")
def process_natural_task(req: NaturalTaskRequest):
    """Process a natural language prompt, routing to the appropriate agent or knowledge base."""
    query = req.query.strip()
    q_lower = query.lower()
    target_agent = (req.target_agent or "auto").strip().lower()

    # Detect if user is asking a question or seeking technical/coding explanations
    is_question = (
        any(q_lower.startswith(w) for w in [
            "what", "how", "why", "who", "when", "where", "which",
            "can you", "could you", "tell me", "explain", "is there",
            "are there", "do you", "describe", "calculate", "solve",
            "help", "write", "generate", "give me", "show me", "define"
        ])
        or "?" in query
        or any(k in q_lower for k in [
            "how to", "how do", "how can", "syntax for", "difference between",
            "error:", "exception:", "bug in", "fix this", "solve java", "solve python"
        ])
    )

    # Detect explicit batch actions on files or specific workflow triggers
    is_explicit_organize = (
        not is_question and (
            any(k in q_lower for k in ["organize files", "sort files", "clean inbox", "organize downloads", "sort inbox", "organize demo_data", "sort documents"])
            or (q_lower.startswith("organize") and any(k in q_lower for k in ["inbox", "file", "folder", "download", "directory"]))
        )
    )
    is_explicit_clean = (
        not is_question and (
            any(k in q_lower for k in [".csv", ".xlsx", "raw_sales", "sales dirty", "scrub csv", "clean dataset", "profile data", "profile csv"])
            or (q_lower.startswith("clean") and any(k in q_lower for k in ["data", "csv", "sales", "file", "dataset", "table", "record"]))
        )
    )
    is_explicit_research = (
        not is_question and (
            any(k in q_lower for k in ["research brief", "market analysis", "brief on", "synthesize report", "intelligence brief"])
            or (q_lower.startswith("research") and not any(q_lower.startswith(w) for w in ["research how", "research why", "research can"]))
        )
    )
    is_explicit_triage = (
        not is_question and any(k in q_lower for k in [
            "triage email", "triage tickets", "triage inquiries", "triage urgent", "triage customer",
            "inquiry:", "ticket:", "subject:", "customer query", "customer queries"
        ])
    )

    # 1. Dedicated File Organizer Action
    if target_agent == "organizer" and is_explicit_organize or (target_agent == "auto" and is_explicit_organize):
        agent = FileOrganizerAgent()
        agent.add_listener(sync_event_emitter)
        res = agent.organize_directory()
        return {
            "agent": "FileOrganizerAgent",
            "type": "organizer",
            "reply": f"**Task Complete:** Successfully organized {res.get('total_processed', 0)} files into categorized folders (`/Invoices`, `/Contracts`, `/Reports`, `/Notes`).\n\n- {res.get('summary', '')}",
            "records": res.get("records", []),
            "artifacts": ["organization_manifest.json", "organization_manifest.md"],
        }

    # 2. Dedicated Research Brief Action
    elif target_agent == "research" and is_explicit_research or (target_agent == "auto" and is_explicit_research):
        agent = ResearchAgent()
        agent.add_listener(sync_event_emitter)
        topic = query
        for prefix in ["research on", "research", "brief on", "search for"]:
            if q_lower.startswith(prefix):
                topic = query[len(prefix):].strip(" :,-")
                break
        res = agent.research(topic=topic or "AI Agent Automation")
        return {
            "agent": "ResearchAgent",
            "type": "research",
            "reply": f"**Executive Intelligence Brief Generated:**\n\n{res.get('full_content', '')}",
            "artifacts": [res.get("markdown_report"), res.get("html_report")],
        }

    # 3. Dedicated Data Cleaner Action
    elif target_agent == "cleaner" and is_explicit_clean or (target_agent == "auto" and is_explicit_clean):
        agent = DataCleanerAgent()
        agent.add_listener(sync_event_emitter)
        target_file = str(config.BASE_DIR / "demo_data" / "raw_sales_dirty.csv")
        res = agent.clean_and_analyze(file_path=target_file)
        changes = res.get("changes", {})
        return {
            "agent": "DataCleanerAgent",
            "type": "cleaner",
            "reply": (
                f"**Data Hygiene & Audit Complete:**\n\n"
                f"- **Scrubbed Duplicates:** {changes.get('duplicates_removed', 0)}\n"
                f"- **Imputed Null Values:** {sum(changes.get('imputed_columns', {}).values())}\n"
                f"- **Normalized Outliers:** {changes.get('outliers_adjusted', 0)}\n"
                f"- **Final Clean Records:** {changes.get('final_rows', 0)}\n\n"
                f"### Executive Insights\n{res.get('insights', '')}"
            ),
            "artifacts": [res.get("markdown_report"), res.get("html_report"), "cleaned_raw_sales_dirty.csv"],
        }

    # 4. Dedicated Email Triage Action
    elif target_agent == "triage" and is_explicit_triage or (target_agent == "auto" and is_explicit_triage):
        agent = EmailTriageAgent()
        agent.add_listener(sync_event_emitter)
        res = agent.triage_inquiries([
            {
                "sender": "client.urgent@company.com",
                "subject": f"Inquiry: {query[:40]}",
                "body": query,
            }
        ])
        return {
            "agent": "EmailTriageAgent",
            "type": "triage",
            "reply": (
                f"**Inquiry Triaged & Draft Response Generated:**\n\n"
                f"- **Assigned Category:** {res['items'][0]['category']}\n"
                f"- **Urgency Level:** {res['items'][0]['urgency']}\n"
                f"- **Detected Sentiment:** {res['items'][0]['sentiment']}\n\n"
                f"**Drafted Email Response:**\n```\n{res['items'][0]['draft']['body']}\n```"
            ),
            "artifacts": [res.get("report_file")],
        }

    # 5. Conversational AI Assistant (Answering Questions, Coding Help, General Queries)
    else:
        # Search knowledge base for grounding context
        kb_matches = default_knowledge_base.search(query, top_k=1)
        knowledge_context = ""
        if kb_matches and (kb_matches[0].get("lexical_score", 0) >= 3.0 or kb_matches[0].get("semantic_score", 0) >= 0.78):
            top_doc = kb_matches[0]
            knowledge_context = (
                f"\nReference Documentation ({top_doc['title']}):\n"
                f"{top_doc['full_content']}\n"
            )

        # Adapt role based on selected target agent persona
        if target_agent == "cleaner":
            role_name = "Data Engineering & Analytics Specialist"
        elif target_agent == "organizer":
            role_name = "File Systems & Workflow Automation Specialist"
        elif target_agent == "research":
            role_name = "Research Briefing & Intelligence Specialist"
        elif target_agent == "triage":
            role_name = "Communications & Customer Operations Specialist"
        else:
            role_name = "Autonomous Task Automation & Problem Solving Assistant"

        system_instruction = (
            f"You are TaskFlow AI, an intelligent, helpful, and thorough {role_name}. "
            "Answer the user's questions clearly, accurately, and politely. "
            "If the user asks a coding or technical question (e.g. in Java, Python, SQL), "
            "provide clean code examples, step-by-step explanations, and best practices. "
            "Format your answer in clean Markdown."
        )
        if knowledge_context:
            system_instruction += f"\nUse the following official company documentation if relevant to ground your answer:\n{knowledge_context}"

        agent = BaseAgent(
            name="TaskFlowAutonomousAgent",
            role=role_name,
            system_instruction=system_instruction,
            tools=[scan_directory, read_file_snippet, fetch_web_page, search_topics, profile_dataset, clean_dataset],
        )
        agent.add_listener(sync_event_emitter)
        res = agent.run(query)
        return {
            "agent": "TaskFlowAI",
            "type": "custom",
            "reply": res.final_answer,
            "artifacts": [],
        }
