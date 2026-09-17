"""
Autonomous Web Research and Executive Briefing Agent.
Gathers content from web sources, synthesizes trends, detects insights,
and generates formatted executive briefings in Markdown and HTML.
"""

from typing import Dict, Any, List, Optional
import datetime
import re
from taskflow.core.agent import BaseAgent
from taskflow.tools.web_tools import fetch_web_page, search_topics
from taskflow.tools.notification_tools import export_markdown_report, export_html_report
from taskflow import config

class ResearchAgent(BaseAgent):
    def __init__(self, llm_provider=None):
        super().__init__(
            name="ResearchAgent",
            role="Autonomous Market & Tech Intelligence Researcher",
            system_instruction="""You specialize in researching complex topics, summarizing authoritative industry articles,
detecting emerging trends, and distilling raw content into high-impact executive briefs with citations and actionable takeaways.""",
            tools=[fetch_web_page, search_topics, export_markdown_report, export_html_report],
            llm_provider=llm_provider
        )

    def research(self, topic: str, urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """Conduct research on a topic and compile executive briefing."""
        self._emit("start", {"agent": self.name, "topic": topic})
        
        findings = []
        sources = []

        # 1. Gather web sources or targeted search snippets
        if urls:
            for u in urls:
                self._emit("tool_call", {"tool": "fetch_web_page", "parameters": {"url": u}})
                page_data = fetch_web_page(u)
                if page_data.get("status") == "success":
                    findings.append({
                        "title": page_data.get("title", u),
                        "snippet": page_data.get("content", "")[:600],
                        "source": u
                    })
                    sources.append(u)
        
        if not findings:
            self._emit("tool_call", {"tool": "search_topics", "parameters": {"query": topic}})
            findings = search_topics(topic)
            sources = [f["source"] for f in findings]

        # 2. Synthesize Intelligence with LLM
        prompt = f"""Synthesize an executive intelligence brief on the topic: '{topic}'.
Sources and Raw Data:
{findings}

Structure your synthesis with:
1. Executive Summary
2. Key Insights & Industry Trends
3. Strategic Implications & Recommendations
"""
        response = self.llm.generate(
            prompt=prompt,
            system_instruction=self.system_instruction
        )
        content = response.content

        # 3. Export Markdown Brief
        clean_topic = re.sub(r"[^a-zA-Z0-9_-]", "_", topic).strip("_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        md_filename = f"research_brief_{clean_topic}_{timestamp}.md"
        html_filename = f"research_brief_{clean_topic}_{timestamp}.html"

        md_path = export_markdown_report(
            title=f"Executive Brief: {topic}",
            content=f"{content}\n\n### References\n" + "\n".join([f"- [{s}]({s})" for s in sources]),
            filename=md_filename
        )

        # 4. Export HTML Brief
        details_html = f"""
        <h2>Key Intelligence Highlights</h2>
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
          <pre style="white-space: pre-wrap; font-family: inherit; margin: 0;">{content}</pre>
        </div>
        <h3>Consulted Sources</h3>
        <ul>
          {"".join([f"<li><a href='{s}' target='_blank'>{s}</a></li>" for s in sources])}
        </ul>
        """
        export_html_report(
            title=f"Intelligence Briefing: {topic}",
            summary=f"Automated synthesis covering {len(findings)} primary sources and industry insights.",
            details_html=details_html,
            filename=html_filename
        )

        result = {
            "topic": topic,
            "summary": content[:300] + "...",
            "full_content": content,
            "markdown_report": md_filename,
            "html_report": html_filename,
            "sources_analyzed": len(findings)
        }
        self._emit("finish", result)
        return result
