"""
Task Automation Scheduler for recurring periodic agent jobs.
"""

from typing import Callable, Dict, Any, List, Optional
import threading
import time
import datetime
import logging

logger = logging.getLogger("taskflow.automation.scheduler")

class ScheduledJob:
    def __init__(self, name: str, interval_seconds: int, task_func: Callable[[], Any], description: str = ""):
        self.name = name
        self.interval_seconds = interval_seconds
        self.task_func = task_func
        self.description = description
        self.last_run: Optional[datetime.datetime] = None
        self.next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval_seconds)
        self.run_count = 0
        self.last_status = "Pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "interval_seconds": self.interval_seconds,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "last_status": self.last_status
        }


class TaskScheduler:
    def __init__(self):
        self.jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_job(self, name: str, interval_seconds: int, task_func: Callable[[], Any], description: str = ""):
        self.jobs[name] = ScheduledJob(name, interval_seconds, task_func, description)
        logger.info(f"Registered scheduled job: {name} (every {interval_seconds}s)")

    def start(self, daemon: bool = True):
        """Start scheduler in background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=daemon)
        self._thread.start()
        logger.info("Task Scheduler started.")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("Task Scheduler stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [j.to_dict() for j in self.jobs.values()]

    def _scheduler_loop(self):
        while self._running:
            now = datetime.datetime.now()
            for job in self.jobs.values():
                if now >= job.next_run:
                    logger.info(f"Running scheduled job: {job.name}")
                    try:
                        job.task_func()
                        job.last_status = "Success"
                    except Exception as e:
                        logger.error(f"Scheduled job {job.name} failed: {e}", exc_info=True)
                        job.last_status = f"Error: {str(e)}"
                    job.last_run = now
                    job.run_count += 1
                    job.next_run = now + datetime.timedelta(seconds=job.interval_seconds)

            time.sleep(1.0)
