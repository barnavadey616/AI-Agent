"""
Document and Inbox Organizer Agent.
Scans messy directories, inspects file contents, categorizes, standardizes filenames,
moves files into organized structures, and generates audit manifests.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import re
import datetime
import logging
from taskflow.core.agent import BaseAgent, AgentRunResult
from taskflow.tools.file_tools import scan_directory, read_file_snippet, organize_file, generate_manifest
from taskflow import config

logger = logging.getLogger("taskflow.agents.file_organizer")

class FileOrganizerAgent(BaseAgent):
    def __init__(self, llm_provider=None):
        super().__init__(
            name="FileOrganizerAgent",
            role="Autonomous Document & Asset Organizer",
            system_instruction="""You specialize in organizing messy downloads, incoming folders, and document repositories.
You inspect file snippets, accurately classify them into categories (Invoices, Contracts, Reports, Data, Code, Notes),
generate clean standardized filenames with date prefixes (e.g., YYYY_Category_Title.ext),
move files cleanly, and produce an audit log.""",
            tools=[scan_directory, read_file_snippet, organize_file, generate_manifest],
            llm_provider=llm_provider
        )

    def organize_directory(self, source_dir: Optional[str] = None, target_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute automated organization pipeline over a directory."""
        src = Path(source_dir) if source_dir else config.WATCH_DIR
        tgt = Path(target_dir) if target_dir else config.ORGANIZED_DIR

        if not src.is_absolute():
            src = config.BASE_DIR / src
        if not tgt.is_absolute():
            tgt = config.BASE_DIR / tgt

        logger.info(f"Starting organization: {src} -> {tgt}")
        self._emit("start", {"agent": self.name, "source": str(src), "target": str(tgt)})

        files = scan_directory(str(src))
        if not files or (len(files) == 1 and "error" in files[0]):
            return {
                "success": True,
                "message": f"No files found to organize in {src}",
                "records": []
            }

        records = []
        today_year = datetime.datetime.now().year

        for f in files:
            file_path = f["path"]
            filename = f["name"]
            snippet = read_file_snippet(file_path, max_chars=1500)

            # Heuristic & Content Classification
            category, clean_title = self._classify_file(filename, snippet)
            clean_title = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_title).strip("_")
            clean_filename = f"{today_year}_{clean_title}{Path(filename).suffix}"

            # Move and organize
            result = organize_file(
                source_path=file_path,
                category=category,
                new_filename=clean_filename,
                target_base_dir=str(tgt)
            )
            records.append(result)

            self._emit("tool_result", {
                "tool": "organize_file",
                "file": filename,
                "category": category,
                "new_filename": clean_filename
            })

        # Generate manifest
        manifest_msg = generate_manifest(records, f"manifest_{int(datetime.datetime.now().timestamp())}.json")

        summary = f"Processed and organized {len(records)} files into {tgt.name}/. {manifest_msg}"
        self._emit("finish", {"summary": summary, "records": records})

        return {
            "success": True,
            "total_processed": len(records),
            "summary": summary,
            "records": records
        }

    def _classify_file(self, filename: str, content: str) -> (str, str):
        """Intelligently classify file type and extract clean descriptive title."""
        text = (filename + " " + content).lower()
        stem = Path(filename).stem
        clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem).strip("_")

        if re.search(r"\b(invoice|bill|receipt|amount due|payment terms|total usd)\b", text):
            # Extract vendor if found on the same line
            vendor_match = re.search(r"(?:vendor|from|company|to):\s*([^\r\n,;]+)", content, re.IGNORECASE)
            raw_vendor = vendor_match.group(1).strip() if vendor_match else clean_stem
            safe_vendor = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_vendor).strip("_")
            title = f"Invoice_{safe_vendor}"
            return "Invoices", title

        if re.search(r"\b(contract|agreement|nda|confidentiality|terms and conditions|signed|signature)\b", text):
            return "Contracts", f"Contract_{clean_stem}"

        if re.search(r"\b(report|quarterly|metrics|kpi|executive summary|performance review|q[1-4])\b", text):
            return "Reports", f"Report_{clean_stem}"

        if re.search(r"\b(csv|json|dataset|dataframe|tabular|sales_data)\b", text):
            return "Data", f"Data_{clean_stem}"

        if re.search(r"\b(def|class|import|function|const|script|python)\b", text):
            return "Code", f"Code_{clean_stem}"

        if re.search(r"\b(meeting|agenda|notes|todo|action items|sync)\b", text):
            return "Notes", f"MeetingNotes_{clean_stem}"

        return "General", f"Doc_{clean_stem}"
