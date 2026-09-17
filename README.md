# TaskFlow AI — Autonomous Multi-Agent Automation Hub

[![Python 3.13](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_API-3.8_Flash-8E24AA.svg)](https://ai.google.dev)
[![Tests](https://img.shields.io/badge/Tests-12%20Passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Autonomous AI agents designed specifically to eliminate repetitive workflows.**
> Automate document filing, market intelligence digests, dirty tabular data cleaning & profiling, and email/customer ticket triage — backed by autonomous background directory watchers, periodic scheduling, a rich CLI, and a modern dark-theme Web UI Dashboard.

---

## 🌟 Key Features & Specialized Agents

TaskFlow AI ships with four production-ready autonomous agents tailored for high-frequency repetitive tasks:

### 1. 📂 Document & Inbox Organizer (`FileOrganizerAgent`)
- **Problem**: Downloads folders and inboxes quickly become cluttered with invoices, agreements, notes, and datasets with arbitrary names.
- **Automation**: Scans target directories, reads snippets, extracts metadata (parties, dates, categories), standardizes filenames (e.g. `2026_Invoice_Uber_Technologies.txt`), sorts files into structured subfolders (`/Invoices`, `/Contracts`, `/Reports`, `/Notes`), and compiles an audit manifest (`manifest.json` and `manifest.md`).

### 2. 🌐 Autonomous Research & Executive Briefing (`ResearchAgent`)
- **Problem**: Professionals spend hours every week searching for news, industry releases, or competitive trends.
- **Automation**: Takes any topic or set of URLs, extracts readability text via BeautifulSoup, synthesizes industry trends, quotes, and takeaways, and compiles a publication-ready Executive Brief in both **Markdown** and **HTML Dashboard** formats.

### 3. 📊 Data Quality & Hygiene Cleaner (`DataCleanerAgent`)
- **Problem**: Repetitive manual scrubbing of dirty CSV/Excel spreadsheets (duplicate rows, missing values, inconsistent casing, negative quantity outliers).
- **Automation**: Profiles tabular datasets using Pandas, deduplicates records, imputes missing values (median for numeric, mode/unknown for categorical), clamps negative outliers, normalizes whitespace, exports a pristine `cleaned_<file>.csv`, and generates an Executive Insights narrative.

### 4. ✉️ Inquiries & Email Triage Matrix (`EmailTriageAgent`)
- **Problem**: Repetitive sorting of support tickets, customer inquiries, and sales leads.
- **Automation**: Classifies incoming messages by urgency (High/Medium/Low), category (Billing, Tech Support, Sales, Partnerships), and sentiment (Frustrated/Positive/Neutral). Drafts customized professional email replies and generates an action matrix report.

### 5. ⚡ Background Triggers & Scheduler Engine
- **Directory Watcher (`watcher.py`)**: Asynchronous background thread that monitors `demo_data/inbox/` (or any custom folder) and automatically triggers the Organizer Agent the instant new files arrive.
- **Job Scheduler (`scheduler.py`)**: Interval and periodic scheduler for hands-off background execution of repetitive jobs.

---

## 🚀 Quick Start Guide

### 1. Setup Environment
```bash
# Clone or open directory
cd "e:\AI Agent"

# Activate the virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies (already pinned in requirements.txt)
pip install -r requirements.txt
```

### 2. Configure Environment (.env)
Copy `.env.example` to `.env`:
```ini
# Optional: Provide your Gemini API Key for live Gemini 3.8 Flash reasoning.
# If omitted or left empty, TaskFlow AI seamlessly uses its built-in
# Autonomous Heuristic Simulation Engine for zero-friction offline testing!
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
```

---

## 💻 Command Line Interface (CLI)

TaskFlow AI features a command-line interface with formatted tables, status badges, and logs:

```bash
# 1. Run the Document & Inbox Organizer
python -m taskflow.cli run-organizer --source demo_data/inbox --target demo_data/organized

# 2. Run Autonomous Research Briefing
python -m taskflow.cli run-research --topic "AI Agent Frameworks & Production Automation 2026"

# 3. Profile and Clean Dirty Tabular Data
python -m taskflow.cli run-data-cleaner --file demo_data/raw_sales_dirty.csv

# 4. Triage Incoming Inquiries & Draft Responses
python -m taskflow.cli run-email-triage

# 5. Start Background Folder Watcher (Auto-organizes any file dropped in inbox)
python -m taskflow.cli watch --dir demo_data/inbox

# 6. Launch the Web UI Dashboard Server
python -m taskflow.cli serve --host 127.0.0.1 --port 8000
```

---

## 🌐 Web Dashboard

Start the web server:
```bash
python -m taskflow.cli serve --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to access:
- **One-Click Task Launchers**: Trigger Document Organizing, Research Synthesis, Data Scrubbing, or Email Triage with a click.
- **Live Real-Time Stream**: WebSocket-connected execution monitor displaying agent thoughts, tool calls, and observations.
- **Artifacts Gallery**: View and download generated reports (HTML/Markdown) and cleaned datasets.
- **Directory Watcher Switch**: Enable/disable automatic background folder monitoring directly from the UI.

---

## 🧪 Automated Testing

Run the full automated test suite with pytest:
```bash
pytest tests/ -v
```

All 12 unit and integration tests cover:
- Tool parameter extraction and schema generator
- ReAct agent execution loop and custom tool calls
- Multi-step workflow pipeline chaining
- File organization and directory classification
- Web research synthesis and document generation
- Tabular data profiling, imputation, and outlier clamping
- Inquiry triage classification
- FastAPI REST endpoints and WebSocket stream

---

## 🛠️ Extending TaskFlow AI: Adding Custom Tools & Agents

### Creating a Custom Tool
Any Python function can be decorated with `@tool` to expose it to AI agents:

```python
from taskflow.core.tool import tool

@tool(name="send_webhook", description="Sends a JSON payload to a remote webhook URL.")
def send_webhook(url: str, payload: dict) -> dict:
    import httpx
    response = httpx.post(url, json=payload, timeout=5.0)
    return {"status_code": response.status_code, "response": response.text}
```

### Creating a Custom Agent
```python
from taskflow.core.agent import BaseAgent
from my_tools import send_webhook

agent = BaseAgent(
    name="DevOpsAgent",
    role="CI/CD Alert & Notification Specialist",
    system_instruction="Monitor build statuses and notify on-call channels.",
    tools=[send_webhook]
)

result = agent.run("Check server logs and notify the DevOps webhook if error rate > 5%.")
print(result.final_answer)
```

---

## 📁 Project Architecture

```
e:\AI Agent/
├── .venv/                         # Python Virtual Environment
├── requirements.txt               # Dependencies
├── .env.example                   # Environment configuration template
├── README.md                      # Documentation
│
├── taskflow/                      # Core Package
│   ├── config.py                  # Runtime settings & paths
│   ├── cli.py                     # Rich CLI entry point
│   ├── core/                      # ReAct Engine & Tool Registry
│   │   ├── agent.py               # Base Agent with step-by-step reasoning
│   │   ├── llm_provider.py        # Gemini 3.8 Flash + Simulation Fallback
│   │   ├── tool.py                # Tool decorator & schema generator
│   │   └── workflow.py            # Multi-step pipeline engine
│   ├── tools/                     # Built-in Automation Tools
│   │   ├── file_tools.py          # Scan, inspect, organize, manifest
│   │   ├── web_tools.py           # Web scraper & search synthesis
│   │   ├── data_tools.py          # Pandas tabular hygiene & anomaly detection
│   │   └── notification_tools.py  # Markdown/HTML report formatters
│   ├── agents/                    # Specialized Automation Agents
│   │   ├── file_organizer.py      # Inbox & Document Organizer
│   │   ├── research_agent.py      # Web Research & Executive Briefs
│   │   ├── data_cleaner.py        # Data Quality & Anomaly Cleaner
│   │   └── email_triage.py        # Inquiry & Email Triage Matrix
│   ├── automation/                # Background Schedulers & Watchers
│   │   ├── watcher.py             # File system observer
│   │   └── scheduler.py           # Periodic job scheduler
│   └── server/                    # FastAPI Server & Web Dashboard
│       ├── app.py                 # REST API & WebSockets
│       └── static/                # Single-page Glassmorphic UI (HTML/CSS/JS)
│
├── demo_data/                     # Pre-packaged sample messy files
│   ├── inbox/                     # Sample receipts, bills, notes, reports
│   └── raw_sales_dirty.csv        # Sample messy CSV with anomalies
│
└── tests/                         # Test Suite
    ├── test_core.py               # Agent ReAct loop & tools
    ├── test_agents.py             # 4 specialized agents
    └── test_api.py                # FastAPI endpoints
```

---

## 📄 License
MIT License. Built with ❤️ to automate repetitive digital work.
