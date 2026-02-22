"""
ALD-01 Scheduler / Cron Jobs
Cron-like job scheduling for recurring tasks.
Integrates with the dashboard for visual management.
"""

import os
import time
import json
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.scheduler")


@dataclass
class CronJob:
    """A scheduled recurring job."""
    id: str
    name: str
    description: str
    schedule: str  # e.g. "every 1h", "every 30m", "every 24h", "daily", "hourly"
    handler_name: str  # Name of the registered handler
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0
    run_count: int = 0
    last_error: str = ""
    last_result: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schedule": self.schedule,
            "handler": self.handler_name,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "last_error": self.last_error,
            "last_result": self.last_result[:200] if self.last_result else "",
            "created_at": self.created_at,
        }


def parse_interval(schedule: str) -> float:
    """Parse schedule string to seconds."""
    s = schedule.lower().strip()
    if s == "minutely" or s == "every 1m":
        return 60
    elif s == "every 5m":
        return 300
    elif s == "every 15m":
        return 900
    elif s == "every 30m":
        return 1800
    elif s == "hourly" or s == "every 1h":
        return 3600
    elif s == "every 6h":
        return 21600
    elif s == "every 12h":
        return 43200
    elif s == "daily" or s == "every 24h":
        return 86400
    elif s == "weekly":
        return 604800

    # Parse "every Nm" or "every Nh" or "every Ns"
    import re
    match = re.match(r"every\s+(\d+)\s*(s|m|h|d)", s)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return val * multiplier.get(unit, 60)

    return 3600  # Default: hourly


class Scheduler:
    """
    Cron-like scheduler for ALD-01.
    Manages recurring jobs with visual dashboard integration.
    """

    def __init__(self):
        self._jobs: Dict[str, CronJob] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._persistence_path = os.path.join(CONFIG_DIR, "scheduler.json")
        self._register_builtin_handlers()
        self._load()

    def _register_builtin_handlers(self) -> None:
        """Register built-in job handlers."""
        self._handlers["health_check"] = self._handler_health_check
        self._handlers["backup"] = self._handler_backup
        self._handlers["memory_compact"] = self._handler_memory_compact
        self._handlers["brain_save"] = self._handler_brain_save
        self._handlers["learning_update"] = self._handler_learning_update
        self._handlers["cleanup_temp"] = self._handler_cleanup_temp
        self._handlers["provider_ping"] = self._handler_provider_ping

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a custom job handler."""
        self._handlers[name] = handler

    def add_job(
        self,
        job_id: str,
        name: str,
        schedule: str,
        handler_name: str,
        description: str = "",
        enabled: bool = True,
    ) -> CronJob:
        """Add a new scheduled job."""
        interval = parse_interval(schedule)
        job = CronJob(
            id=job_id,
            name=name,
            description=description,
            schedule=schedule,
            handler_name=handler_name,
            enabled=enabled,
            next_run=time.time() + interval,
        )
        self._jobs[job_id] = job
        self._save()
        logger.info(f"Cron job added: {name} ({schedule})")
        return job

    def remove_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._save()
            return True
        return False

    def enable_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True
            self._save()
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False
            self._save()
            return True
        return False

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        j = self._jobs.get(job_id)
        return j.to_dict() if j else None

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [j.to_dict() for j in sorted(self._jobs.values(), key=lambda x: x.next_run)]

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        self._setup_default_jobs()
        asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        self._running = False

    async def _scheduler_loop(self) -> None:
        while self._running:
            try:
                now = time.time()
                for job in self._jobs.values():
                    if not job.enabled:
                        continue
                    if now >= job.next_run:
                        await self._execute_job(job)
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(30)

    async def _execute_job(self, job: CronJob) -> None:
        handler = self._handlers.get(job.handler_name)
        if not handler:
            job.last_error = f"Handler not found: {job.handler_name}"
            return

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler()
            else:
                result = handler()

            job.last_result = str(result)[:500] if result else "OK"
            job.last_error = ""
            job.run_count += 1

        except Exception as e:
            job.last_error = str(e)

        job.last_run = time.time()
        interval = parse_interval(job.schedule)
        job.next_run = time.time() + interval

        # Save periodically
        if job.run_count % 5 == 0:
            self._save()

    def _setup_default_jobs(self) -> None:
        """Setup default recurring jobs if not already configured."""
        defaults = [
            ("health_check", "Health Check", "every 1h", "health_check", "Run system health check"),
            ("auto_backup", "Auto Backup", "every 6h", "backup", "Automatic data backup"),
            ("memory_compact", "Memory Compact", "every 12h", "memory_compact", "Compact database"),
            ("brain_save", "Brain Save", "every 30m", "brain_save", "Save brain state"),
            ("cleanup_temp", "Temp Cleanup", "daily", "cleanup_temp", "Clean temp files"),
        ]
        for jid, name, schedule, handler, desc in defaults:
            if jid not in self._jobs:
                self.add_job(jid, name, schedule, handler, desc)

    # ──── Built-in handlers ────

    async def _handler_health_check(self) -> str:
        from ald01.core.self_heal import get_self_healing_engine
        result = get_self_healing_engine().run_health_check()
        return f"Checks: {len(result.get('checks', []))}, Fixes: {result.get('fixes_applied', 0)}"

    async def _handler_backup(self) -> str:
        from ald01.core.self_heal import get_self_healing_engine
        path = get_self_healing_engine().backup_data()
        return f"Backup at: {path}"

    async def _handler_memory_compact(self) -> str:
        from ald01.core.self_heal import get_self_healing_engine
        result = get_self_healing_engine().cleanup_memory()
        return str(result)

    async def _handler_brain_save(self) -> str:
        from ald01.core.brain import get_brain
        brain = get_brain()
        brain.record_growth()
        brain.save()
        return f"Brain saved. Nodes: {len(brain._nodes)}"

    async def _handler_learning_update(self) -> str:
        from ald01.core.learning import get_learning_system
        ls = get_learning_system()
        patterns = ls.get_patterns()
        return f"Patterns detected: {len(patterns)}"

    async def _handler_cleanup_temp(self) -> str:
        from ald01.core.data_manager import get_data_manager, DataCategory
        dm = get_data_manager()
        result = dm.reset_temp()
        return f"Cleaned: {result.get('deleted', 0)} temp files"

    async def _handler_provider_ping(self) -> str:
        return "Providers pinged"

    def _save(self) -> None:
        try:
            data = {j.id: {
                "name": j.name, "description": j.description, "schedule": j.schedule,
                "handler_name": j.handler_name, "enabled": j.enabled,
                "last_run": j.last_run, "run_count": j.run_count,
                "created_at": j.created_at,
            } for j in self._jobs.values()}
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Scheduler save failed: {e}")

    def _load(self) -> None:
        try:
            if not os.path.exists(self._persistence_path):
                return
            with open(self._persistence_path, "r") as f:
                data = json.load(f)
            for jid, jdata in data.items():
                interval = parse_interval(jdata.get("schedule", "hourly"))
                self._jobs[jid] = CronJob(
                    id=jid,
                    name=jdata.get("name", jid),
                    description=jdata.get("description", ""),
                    schedule=jdata.get("schedule", "hourly"),
                    handler_name=jdata.get("handler_name", jid),
                    enabled=jdata.get("enabled", True),
                    last_run=jdata.get("last_run", 0),
                    run_count=jdata.get("run_count", 0),
                    next_run=time.time() + interval,
                    created_at=jdata.get("created_at", time.time()),
                )
        except Exception as e:
            logger.warning(f"Scheduler load failed: {e}")


_scheduler: Optional[Scheduler] = None

def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
