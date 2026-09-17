"""
File system watcher for autonomous directory monitoring and trigger execution.
Monitors an inbox folder and automatically launches the FileOrganizerAgent when new files land.
"""

from pathlib import Path
import threading
import time
import logging
from taskflow import config
from taskflow.agents.file_organizer import FileOrganizerAgent

logger = logging.getLogger("taskflow.automation.watcher")

class DirectoryWatcher:
    def __init__(self, watch_dir: Path = config.WATCH_DIR, poll_interval: float = 2.0):
        self.watch_dir = Path(watch_dir)
        if not self.watch_dir.is_absolute():
            self.watch_dir = config.BASE_DIR / self.watch_dir
        self.poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread = None
        self.agent = FileOrganizerAgent()
        self.last_files = set()

    def start(self, daemon: bool = True):
        """Start directory observer in background."""
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self._running = True
        self.last_files = set(f.name for f in self.watch_dir.glob("*") if f.is_file())
        self._thread = threading.Thread(target=self._watch_loop, daemon=daemon)
        self._thread.start()
        logger.info(f"Directory Watcher started on: {self.watch_dir}")

    def stop(self):
        """Stop watcher thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("Directory Watcher stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    def _watch_loop(self):
        while self._running:
            try:
                current_files = set(f.name for f in self.watch_dir.glob("*") if f.is_file())
                new_files = current_files - self.last_files

                if new_files:
                    logger.info(f"Detected {len(new_files)} new files in {self.watch_dir.name}: {new_files}")
                    # Allow slight delay for file writing to finish
                    time.sleep(0.5)
                    # Trigger organizer agent
                    result = self.agent.organize_directory(source_dir=str(self.watch_dir))
                    logger.info(f"Auto-organization complete: {result.get('summary')}")
                    # Update file snapshot
                    self.last_files = set(f.name for f in self.watch_dir.glob("*") if f.is_file())
                else:
                    self.last_files = current_files

            except Exception as e:
                logger.error(f"Error in watcher loop: {e}", exc_info=True)

            time.sleep(self.poll_interval)
