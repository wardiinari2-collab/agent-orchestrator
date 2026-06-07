"""Cron scheduler for recurring tasks."""
from __future__ import annotations
import logging
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .engine import Orchestrator
from .task import Task

logger = logging.getLogger(__name__)


class Scheduler:
    """Manages scheduled (cron) task execution."""

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self._scheduler = BackgroundScheduler()
        self._jobs: dict[str, str] = {}  # task_id -> job_id

    def add_task(self, task: Task) -> None:
        """Schedule a task with its cron expression."""
        if not task.schedule:
            logger.warning(f"Task '{task.name}' has no schedule, skipping")
            return

        trigger = CronTrigger.from_crontab(task.schedule)
        job = self._scheduler.add_job(
            self._run_task,
            trigger=trigger,
            args=[task],
            id=task.id,
            name=task.name,
            replace_existing=True,
        )
        self._jobs[task.id] = job.id
        logger.info(f"Scheduled task '{task.name}' with cron: {task.schedule}")

    def _run_task(self, task: Task) -> None:
        """Execute a scheduled task."""
        logger.info(f"Cron triggered: {task.name}")
        try:
            result = self.orchestrator.execute(task)
            logger.info(f"Cron result: {task.name} -> {result.status.value}")
        except Exception as e:
            logger.error(f"Cron error: {task.name} -> {e}")

    def add_task_file(self, path: str | Path) -> None:
        """Load task from YAML and schedule it."""
        import yaml
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        task = Task.from_dict(data)
        if task.schedule:
            self.add_task(task)
        else:
            logger.warning(f"Task '{task.name}' in {path.name} has no schedule")

    def add_tasks_directory(self, path: str | Path) -> int:
        """Load and schedule all tasks from a directory."""
        path = Path(path)
        if not path.exists():
            return 0
        count = 0
        for f in sorted(path.glob("*.yaml")):
            try:
                self.add_task_file(f)
                count += 1
            except Exception as e:
                logger.error(f"Failed to schedule {f.name}: {e}")
        return count

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        job_id = self._jobs.pop(task_id, None)
        if job_id:
            self._scheduler.remove_job(job_id)
            return True
        return False

    def list_jobs(self) -> list[dict]:
        """List all scheduled jobs."""
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else "N/A",
            })
        return jobs

    def start(self) -> None:
        """Start the scheduler."""
        self._scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self._scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
