"""
Autonomous Email and Inquiry Triage Agent.
Classifies incoming correspondence by urgency, sentiment, and category,
drafts professional responses, and prepares an actionable escalation matrix.
"""

from typing import Dict, Any, List, Optional
import datetime
import re
from taskflow.core.agent import BaseAgent
from taskflow.tools.notification_tools import format_email_draft, export_markdown_report
from taskflow.tools.knowledge_tools import query_knowledge_base
from taskflow import config

class EmailTriageAgent(BaseAgent):
    def __init__(self, llm_provider=None):
        super().__init__(
            name="EmailTriageAgent",
            role="Autonomous Communications & Ticket Triage Specialist",
            system_instruction="""You specialize in triaging repetitive support queries, customer inquiries, and internal emails.
You classify urgency (High/Medium/Low), detect sentiment and intent, draft courteous and effective responses
grounded in company knowledge base policies and SLAs, and identify items requiring human supervisor approval.""",
            tools=[format_email_draft, export_markdown_report, query_knowledge_base],
            llm_provider=llm_provider
        )

    def triage_inquiries(self, inquiries: List[Dict[str, str]]) -> Dict[str, Any]:
        """Triage a list of messages, generate response drafts, and compile an executive triage log."""
        self._emit("start", {"agent": self.name, "count": len(inquiries)})

        results = []
        high_priority_count = 0

        for idx, item in enumerate(inquiries, 1):
            sender = item.get("sender", f"client_{idx}@example.com")
            subject = item.get("subject", "General Inquiry")
            body = item.get("body", "")

            # Query knowledge base for relevant SOPs, SLAs, or refund policies
            kb_matches = query_knowledge_base(f"{subject} {body}", top_k=2)
            kb_context = "\n".join([f"- [{m['title']}]: {m['snippet']}" for m in kb_matches]) if kb_matches else "No specific policy retrieved."

            # Heuristic & LLM classification
            urgency, category, sentiment = self._classify_inquiry(subject, body)
            if urgency == "High":
                high_priority_count += 1

            # Draft response grounded in retrieved knowledge
            prompt = f"""Draft a polite, highly professional and helpful email response to:
Sender: {sender}
Subject: {subject}
Message Body:
{body}

Urgency: {urgency}
Category: {category}
Detected Sentiment: {sentiment}

Relevant Company Policies / Knowledge Base Grounding:
{kb_context}

Provide a crisp, actionable draft addressing their questions, referencing official company SLA or refund terms where applicable."""

            llm_res = self.llm.generate(prompt=prompt, system_instruction=self.system_instruction)
            draft_text = llm_res.content

            # Format draft tool
            draft_record = format_email_draft(
                recipient=sender,
                subject=f"Re: {subject}",
                body=draft_text,
                urgency=urgency,
                category=category
            )

            results.append({
                "id": idx,
                "sender": sender,
                "subject": subject,
                "urgency": urgency,
                "category": category,
                "sentiment": sentiment,
                "draft": draft_record
            })

            self._emit("tool_result", {
                "tool": "format_email_draft",
                "recipient": sender,
                "urgency": urgency,
                "category": category
            })

        # Generate triage matrix report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = f"email_triage_log_{timestamp}.md"
        
        table_rows = []
        for r in results:
            urgency_badge = "🔴 High" if r["urgency"] == "High" else ("🟡 Medium" if r["urgency"] == "Medium" else "🟢 Low")
            table_rows.append(f"| {r['id']} | `{r['sender']}` | {r['subject']} | **{r['category']}** | {urgency_badge} | {r['sentiment']} |")

        md_content = f"""
## Inquiries Triage Summary
- Total Processed: {len(results)}
- High Urgency (Escalated): {high_priority_count}
- Drafts Prepared: {len(results)}

| ID | Sender | Subject | Category | Urgency | Sentiment |
|---|---|---|---|---|---|
{"\n".join(table_rows)}

### Draft Details
All response drafts have been prepared and logged in the reports directory for review.
"""
        export_markdown_report(
            title="Inquiries & Email Triage Matrix",
            content=md_content,
            filename=md_file
        )

        final_summary = {
            "total_processed": len(results),
            "high_urgency_count": high_priority_count,
            "report_file": md_file,
            "items": results
        }
        self._emit("finish", final_summary)
        return final_summary

    def _classify_inquiry(self, subject: str, body: str) -> (str, str, str):
        """Classify urgency, category, and sentiment."""
        text = (subject + " " + body).lower()
        
        # Urgency
        if any(w in text for w in ["urgent", "down", "outage", "broken", "critical", "immediately", "asap", "dispute", "cancel", "refund"]):
            urgency = "High"
        elif any(w in text for w in ["pricing", "demo", "proposal", "contract", "bug", "error"]):
            urgency = "Medium"
        else:
            urgency = "Low"

        # Category
        if any(w in text for w in ["invoice", "bill", "payment", "charge", "refund"]):
            category = "Billing"
        elif any(w in text for w in ["bug", "error", "broken", "failed", "crash", "login", "down"]):
            category = "Technical Support"
        elif any(w in text for w in ["pricing", "demo", "quote", "sales", "enterprise", "purchase"]):
            category = "Sales"
        elif any(w in text for w in ["partner", "integrate", "collab"]):
            category = "Partnerships"
        else:
            category = "General"

        # Sentiment
        if any(w in text for w in ["unacceptable", "furious", "terrible", "frustrated", "worst", "angry"]):
            sentiment = "Frustrated"
        elif any(w in text for w in ["love", "great", "thank", "awesome", "excited", "congrats"]):
            sentiment = "Positive"
        else:
            sentiment = "Neutral"

        return urgency, category, sentiment
