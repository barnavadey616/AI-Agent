"""
Configuration module for TaskFlow AI.
Manages environment variables, default paths, and runtime settings.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
TASKFLOW_MODE = os.getenv("TASKFLOW_MODE", "auto").lower()

# Determine effective mode
if TASKFLOW_MODE == "auto":
    IS_SIMULATION = not bool(GEMINI_API_KEY)
elif TASKFLOW_MODE == "simulation":
    IS_SIMULATION = True
else:
    IS_SIMULATION = False

# Directories
WATCH_DIR = BASE_DIR / os.getenv("WATCH_DIR", "demo_data/inbox")
ORGANIZED_DIR = BASE_DIR / os.getenv("ORGANIZED_DIR", "demo_data/organized")
OUTPUTS_DIR = BASE_DIR / os.getenv("OUTPUTS_DIR", "outputs")
KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"
REPORTS_DIR = OUTPUTS_DIR / "reports"
CLEANED_DATA_DIR = OUTPUTS_DIR / "cleaned_data"
LOGS_DIR = OUTPUTS_DIR / "logs"

# Server
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

def ensure_directories():
    """Ensure all runtime directories exist."""
    for path in [WATCH_DIR, ORGANIZED_DIR, OUTPUTS_DIR, KNOWLEDGE_DIR, REPORTS_DIR, CLEANED_DATA_DIR, LOGS_DIR]:
        path.mkdir(parents=True, exist_ok=True)

ensure_directories()
