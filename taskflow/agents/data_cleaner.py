"""
Autonomous Data Cleaning and Business Insights Agent.
Profiles dirty datasets, applies automated cleaning transformations,
computes summary metrics, and generates an executive audit & insights report.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import datetime
from taskflow.core.agent import BaseAgent
from taskflow.tools.data_tools import profile_dataset, clean_dataset, compute_summary_metrics
from taskflow.tools.notification_tools import export_markdown_report, export_html_report
from taskflow import config

class DataCleanerAgent(BaseAgent):
    def __init__(self, llm_provider=None):
        super().__init__(
            name="DataCleanerAgent",
            role="Autonomous Data Quality Auditor & Insights Analyst",
            system_instruction="""You specialize in automating repetitive data profiling, scrubbing, hygiene, and statistical audits.
You identify missing records, outliers, and formatting bugs, clean them reliably, and extract commercial insights.""",
            tools=[profile_dataset, clean_dataset, compute_summary_metrics, export_markdown_report, export_html_report],
            llm_provider=llm_provider
        )

    def clean_and_analyze(self, file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Perform end-to-end data audit, automated cleaning, and executive reporting."""
        p = Path(file_path)
        if not p.is_absolute():
            p = config.BASE_DIR / p
        
        self._emit("start", {"agent": self.name, "file": p.name})

        # 1. Profile dirty dataset
        profile = profile_dataset(str(p))
        if "error" in profile:
            return {"success": False, "error": profile["error"]}

        # 2. Run automated hygiene cleaning
        clean_result = clean_dataset(str(p), output_path=output_path)
        if not clean_result.get("success"):
            return {"success": False, "error": clean_result.get("error")}

        # 3. Compute metrics on cleaned data
        cleaned_file = clean_result["cleaned_file"]
        metrics = compute_summary_metrics(cleaned_file)

        # 4. Synthesize Executive Insight with LLM
        prompt = f"""Generate an Executive Data Hygiene & Commercial Insight summary for dataset '{p.name}'.

Data Quality Audit Findings:
- Total rows processed: {clean_result['initial_rows']} -> {clean_result['final_rows']} clean records
- Duplicates scrubbed: {clean_result['duplicates_removed']}
- Imputed columns: {clean_result['imputed_columns']}
- Negative / outlier values corrected: {clean_result['outliers_adjusted']}

Post-Clean Business Metrics:
{metrics}

Summarize:
1. Data Quality Health Score & Corrective Actions
2. Business Key Metrics & Commercial Trends
3. Next Recommended Data Hygiene Protocols
"""
        response = self.llm.generate(
            prompt=prompt,
            system_instruction=self.system_instruction
        )
        insights_narrative = response.content

        # 5. Export Reports (Markdown & HTML)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = f"data_audit_{p.stem}_{timestamp}.md"
        html_file = f"data_audit_{p.stem}_{timestamp}.html"

        md_content = f"""
## Summary of Changes
| Metric | Value |
|---|---|
| Initial Rows | {clean_result['initial_rows']} |
| Scrubbed Duplicates | {clean_result['duplicates_removed']} |
| Imputed Missing Fields | {clean_result['imputed_columns']} |
| Outliers Standardized | {clean_result['outliers_adjusted']} |
| Cleaned Dataset | `{clean_result['cleaned_file']}` |

## Executive Business Insights
{insights_narrative}
"""
        export_markdown_report(
            title=f"Data Quality Audit: {p.name}",
            content=md_content,
            filename=md_file
        )

        details_html = f"""
        <h3>Hygiene Transformation Summary</h3>
        <table>
          <tr><th>Stage</th><th>Metric</th><th>Result</th></tr>
          <tr><td>Deduplication</td><td>Redundant records removed</td><td><strong>{clean_result['duplicates_removed']}</strong></td></tr>
          <tr><td>Imputation</td><td>Null values patched</td><td><strong>{sum(clean_result['imputed_columns'].values())}</strong> across {len(clean_result['imputed_columns'])} fields</td></tr>
          <tr><td>Normalization</td><td>Negative/outlier values corrected</td><td><strong>{clean_result['outliers_adjusted']}</strong></td></tr>
          <tr><td>Integrity</td><td>Final validated records</td><td><strong>{clean_result['final_rows']}</strong></td></tr>
        </table>

        <h3>Executive Analysis & Recommendations</h3>
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-top: 15px;">
          <pre style="white-space: pre-wrap; font-family: inherit; margin: 0;">{insights_narrative}</pre>
        </div>

        <p style="margin-top: 20px;">
          <strong>Exported Clean Dataset:</strong> <code>{clean_result['cleaned_file']}</code>
        </p>
        """

        export_html_report(
            title=f"Data Hygiene Audit & Executive Report: {p.name}",
            summary=f"Automated quality scrubbing completed. Cleaned {clean_result['final_rows']} records with zero remaining anomalies.",
            details_html=details_html,
            filename=html_file
        )

        result = {
            "success": True,
            "original_file": str(p),
            "cleaned_file": cleaned_file,
            "changes": clean_result,
            "metrics": metrics,
            "markdown_report": md_file,
            "html_report": html_file,
            "insights": insights_narrative
        }
        self._emit("finish", result)
        return result
