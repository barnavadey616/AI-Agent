"""
Command Line Interface for TaskFlow AI.
Provides rich terminal workflows for executing agents, watching folders, and launching the Web UI.
"""

import argparse
import sys
import os
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
import uvicorn

from taskflow import config
from taskflow.agents.file_organizer import FileOrganizerAgent
from taskflow.agents.research_agent import ResearchAgent
from taskflow.agents.data_cleaner import DataCleanerAgent
from taskflow.agents.email_triage import EmailTriageAgent
from taskflow.automation.watcher import DirectoryWatcher

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

def print_banner():
    banner = """
=============================================================
                     TASKFLOW AI
        Autonomous Multi-Agent Task Automation Hub
        Powered by Gemini 3.8 Flash & Heuristic Engine
=============================================================
    """
    console.print(Panel(banner.strip(), style="bold cyan"))

def handle_organizer(args):
    console.print("[bold blue]Starting Document & Inbox Organizer Agent...[/bold blue]")
    agent = FileOrganizerAgent()
    
    # Event hooks
    agent.add_listener(lambda event, data: console.print(f"  [dim cyan]► [{event}][/dim cyan] {data}"))
    
    result = agent.organize_directory(source_dir=args.source, target_dir=args.target)
    
    table = Table(title="Organization Results", show_header=True, header_style="bold magenta")
    table.add_column("Original File", style="dim")
    table.add_column("Category", style="cyan")
    table.add_column("Organized File", style="green")
    
    for rec in result.get("records", []):
        table.add_row(
            Path(rec.get("original_path", "")).name,
            rec.get("category", ""),
            rec.get("filename", "")
        )
    console.print(table)
    console.print(f"[bold green][OK] {result.get('summary')}[/bold green]")

def handle_research(args):
    console.print(f"[bold blue]Conducting automated research on: '{args.topic}'[/bold blue]")
    agent = ResearchAgent()
    urls = [u.strip() for u in args.urls.split(",")] if args.urls else None
    
    agent.add_listener(lambda event, data: console.print(f"  [dim cyan]-> [{event}][/dim cyan] {data}"))
    result = agent.research(topic=args.topic, urls=urls)
    
    console.print(Panel(result.get("full_content", ""), title=f"Executive Brief: {args.topic}", style="bold green"))
    console.print(f"[bold green][OK] Saved Markdown:[/bold green] outputs/reports/{result.get('markdown_report')}")
    console.print(f"[bold green][OK] Saved HTML Dashboard:[/bold green] outputs/reports/{result.get('html_report')}")

def handle_data_cleaner(args):
    console.print(f"[bold blue]Profiling and Cleaning Dataset: '{args.file}'[/bold blue]")
    agent = DataCleanerAgent()
    agent.add_listener(lambda event, data: console.print(f"  [dim cyan]-> [{event}][/dim cyan] {data}"))
    
    result = agent.clean_and_analyze(file_path=args.file, output_path=args.output)
    if not result.get("success"):
        console.print(f"[bold red][ERROR] Failed: {result.get('error')}[/bold red]")
        return

    changes = result["changes"]
    table = Table(title="Data Quality Hygiene Audit", show_header=True, header_style="bold green")
    table.add_column("Hygiene Metric", style="cyan")
    table.add_column("Result", style="yellow")
    
    table.add_row("Initial Records", str(changes["initial_rows"]))
    table.add_row("Duplicates Removed", str(changes["duplicates_removed"]))
    table.add_row("Imputed Null Values", str(sum(changes["imputed_columns"].values())))
    table.add_row("Negative Outliers Standardized", str(changes["outliers_adjusted"]))
    table.add_row("Final Clean Records", str(changes["final_rows"]))
    
    console.print(table)
    console.print(Panel(result.get("insights", ""), title="Executive Business Insights", style="bold cyan"))
    console.print(f"[bold green][OK] Cleaned Data Exported:[/bold green] {result.get('cleaned_file')}")
    console.print(f"[bold green][OK] Audit Report:[/bold green] outputs/reports/{result.get('html_report')}")

def handle_email_triage(args):
    console.print("[bold blue]Running Email & Customer Query Triage Agent...[/bold blue]")
    agent = EmailTriageAgent()
    agent.add_listener(lambda event, data: console.print(f"  [dim cyan]-> [{event}][/dim cyan] {data}"))

    # Sample demo inquiries if none provided
    sample_inquiries = [
        {
            "sender": "sarah.finance@acme.org",
            "subject": "URGENT: Billing discrepancy on Invoice #4092",
            "body": "Hi, our finance team noticed a double charge of $12,500 on our latest cycle. We need this resolved and refunded ASAP before our board audit."
        },
        {
            "sender": "kevin@startupflow.io",
            "subject": "Enterprise Demo & Custom Tool Integration",
            "body": "Hello! We love TaskFlow and want to schedule a 30-min demo for our 50-person engineering team to automate our weekly release QA."
        },
        {
            "sender": "marketing-updates@newsletters.com",
            "subject": "Weekly Tech Trends Roundup #89",
            "body": "Here are this week's top 10 articles on cloud architectures and DevOps tooling."
        }
    ]

    result = agent.triage_inquiries(sample_inquiries)
    
    table = Table(title="Email Triage & Action Matrix", show_header=True, header_style="bold magenta")
    table.add_column("Sender", style="dim")
    table.add_column("Subject", style="cyan")
    table.add_column("Category", style="yellow")
    table.add_column("Urgency", style="red")
    table.add_column("Sentiment", style="green")

    for item in result.get("items", []):
        table.add_row(
            item["sender"],
            item["subject"][:30] + "...",
            item["category"],
            item["urgency"],
            item["sentiment"]
        )
    console.print(table)
    console.print(f"[bold green]✓ Triage Report & Drafts Saved:[/bold green] outputs/reports/{result.get('report_file')}")

def handle_watch(args):
    console.print(f"[bold yellow]Starting Directory Watcher on: {args.dir}[/bold yellow]")
    console.print("Drop any messy files into this directory. The FileOrganizerAgent will auto-classify and sort them.")
    console.print("Press Ctrl+C to stop.")
    
    watcher = DirectoryWatcher(watch_dir=args.dir)
    watcher.start(daemon=False)

def handle_serve(args):
    console.print(f"[bold green]Starting TaskFlow Web UI Server on http://{args.host}:{args.port}[/bold green]")
    uvicorn.run("taskflow.server.app:app", host=args.host, port=args.port, reload=False)

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="TaskFlow AI - Autonomous Task Automation CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Organizer
    p_org = subparsers.add_parser("run-organizer", help="Organize and classify messy files")
    p_org.add_argument("--source", default="demo_data/inbox", help="Source directory containing unorganized files")
    p_org.add_argument("--target", default="demo_data/organized", help="Destination base directory")

    # Research
    p_res = subparsers.add_parser("run-research", help="Automated web research & executive brief")
    p_res.add_argument("--topic", required=True, help="Topic or query to research")
    p_res.add_argument("--urls", default=None, help="Comma-separated list of URLs to fetch")

    # Data Cleaner
    p_data = subparsers.add_parser("run-data-cleaner", help="Profile and clean tabular data (CSV/Excel)")
    p_data.add_argument("--file", required=True, help="Path to dirty CSV file")
    p_data.add_argument("--output", default=None, help="Target clean CSV path")

    # Email Triage
    p_mail = subparsers.add_parser("run-email-triage", help="Triage inquiries and draft responses")

    # Watcher
    p_watch = subparsers.add_parser("watch", help="Watch an inbox folder and auto-organize incoming files")
    p_watch.add_argument("--dir", default="demo_data/inbox", help="Directory to monitor")

    # Web Server
    p_serve = subparsers.add_parser("serve", help="Start the FastAPI Web UI Dashboard")
    p_serve.add_argument("--host", default="127.0.0.1", help="Server host")
    p_serve.add_argument("--port", type=int, default=8000, help="Server port")

    args = parser.parse_args()

    if args.command == "run-organizer":
        handle_organizer(args)
    elif args.command == "run-research":
        handle_research(args)
    elif args.command == "run-data-cleaner":
        handle_data_cleaner(args)
    elif args.command == "run-email-triage":
        handle_email_triage(args)
    elif args.command == "watch":
        handle_watch(args)
    elif args.command == "serve":
        handle_serve(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
