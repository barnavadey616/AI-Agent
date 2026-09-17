"""
Shared background automation services (Watcher and Scheduler).
"""

from taskflow.automation.watcher import DirectoryWatcher
from taskflow.automation.scheduler import TaskScheduler

watcher = DirectoryWatcher()
scheduler = TaskScheduler()
