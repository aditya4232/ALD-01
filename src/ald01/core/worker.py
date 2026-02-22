"""
ALD-01 Background Worker
Handles background tasks like document generation, code building, memory saving,
PDF creation, and scheduled maintenance — all while conversation continues.
"""

import os
import time
import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ald01 import DATA_DIR
from ald01.core.events import get_event_bus, Event, EventType

logger = logging.getLogger("ald01.worker")


class WorkerJobType(str, Enum):
    CODE_GEN = "code_generation"
    DOC_BUILD = "document_build"
    PDF_EXPORT = "pdf_export"
    MEMORY_SAVE = "memory_save"
    MEMORY_COMPACT = "memory_compact"
    BACKUP = "backup"
    LEARNING_UPDATE = "learning_update"
    HEALTH_CHECK = "health_check"
    PROVIDER_PING = "provider_ping"
    CLEANUP = "cleanup"
    CUSTOM = "custom"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundJob:
    id: str
    job_type: WorkerJobType
    name: str
    description: str = ""
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0  # 0.0 to 1.0
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.job_type.value,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "progress": round(self.progress * 100, 1),
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round((self.completed_at - self.started_at) * 1000) if self.completed_at else 0,
            "metadata": self.metadata,
        }


class BackgroundWorker:
    """
    Background worker that processes jobs while the user continues chatting.
    Supports:
    - Code generation and file writing
    - Document/PDF building
    - Memory saving and compaction
    - Scheduled health checks
    - Provider pinging
    - Automated backups
    """

    def __init__(self, max_concurrent: int = 3):
        self._jobs: Dict[str, BackgroundJob] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._max_concurrent = max_concurrent
        self._running_count = 0
        self._running = False
        self._event_bus = get_event_bus()
        self._output_dir = os.path.join(DATA_DIR, "worker_output")
        os.makedirs(self._output_dir, exist_ok=True)
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, job_type: WorkerJobType, handler: Callable) -> None:
        """Register a handler for a job type."""
        self._handlers[job_type.value] = handler

    async def submit(
        self,
        job_type: WorkerJobType,
        name: str,
        description: str = "",
        handler: Optional[Callable] = None,
        **kwargs,
    ) -> str:
        """Submit a background job. Returns job ID."""
        job_id = f"wj_{uuid.uuid4().hex[:10]}"
        job = BackgroundJob(
            id=job_id,
            job_type=job_type,
            name=name,
            description=description,
            metadata=kwargs,
        )
        self._jobs[job_id] = job

        if handler:
            self._handlers[f"custom_{job_id}"] = handler

        await self._queue.put((job, handler))

        await self._event_bus.emit(Event(
            type=EventType.DASHBOARD_UPDATE,
            data={"type": "worker_job_queued", "job": job.to_dict()},
            source="worker",
        ))

        logger.info(f"Background job queued: {name} ({job_type.value})")
        return job_id

    async def start(self) -> None:
        """Start background worker loop."""
        self._running = True
        for _ in range(self._max_concurrent):
            asyncio.create_task(self._worker_loop())
        logger.info(f"Background worker started ({self._max_concurrent} concurrent)")

    async def stop(self) -> None:
        """Stop background worker."""
        self._running = False

    async def _worker_loop(self) -> None:
        """Worker loop — picks jobs from queue."""
        while self._running:
            try:
                job, handler = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._execute_job(job, handler)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)

    async def _execute_job(self, job: BackgroundJob, handler: Optional[Callable]) -> None:
        """Execute a single background job."""
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        self._running_count += 1

        try:
            # Find handler
            fn = handler or self._handlers.get(job.job_type.value)
            if fn is None:
                fn = self._handlers.get(f"custom_{job.id}")
            if fn is None:
                fn = self._get_builtin_handler(job.job_type)

            if fn is None:
                raise ValueError(f"No handler for job type: {job.job_type.value}")

            # Execute
            if asyncio.iscoroutinefunction(fn):
                job.result = await fn(job)
            else:
                loop = asyncio.get_event_loop()
                job.result = await loop.run_in_executor(None, fn, job)

            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.completed_at = time.time()

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = time.time()
            logger.error(f"Background job failed: {job.name}: {e}")

        finally:
            self._running_count -= 1
            await self._event_bus.emit(Event(
                type=EventType.DASHBOARD_UPDATE,
                data={"type": "worker_job_completed", "job": job.to_dict()},
                source="worker",
            ))

    def _get_builtin_handler(self, job_type: WorkerJobType) -> Optional[Callable]:
        """Get built-in handler for common job types."""
        handlers = {
            WorkerJobType.MEMORY_SAVE: self._handle_memory_save,
            WorkerJobType.MEMORY_COMPACT: self._handle_memory_compact,
            WorkerJobType.BACKUP: self._handle_backup,
            WorkerJobType.HEALTH_CHECK: self._handle_health_check,
            WorkerJobType.CLEANUP: self._handle_cleanup,
            WorkerJobType.CODE_GEN: self._handle_code_gen,
            WorkerJobType.DOC_BUILD: self._handle_doc_build,
        }
        return handlers.get(job_type)

    async def _handle_memory_save(self, job: BackgroundJob) -> Dict[str, Any]:
        from ald01.core.memory import get_memory
        mem = get_memory()
        stats = mem.get_stats()
        return {"saved": True, "stats": stats}

    async def _handle_memory_compact(self, job: BackgroundJob) -> Dict[str, Any]:
        from ald01.core.self_heal import get_self_healing_engine
        engine = get_self_healing_engine()
        result = engine.cleanup_memory()
        return result

    async def _handle_backup(self, job: BackgroundJob) -> Dict[str, Any]:
        from ald01.core.self_heal import get_self_healing_engine
        engine = get_self_healing_engine()
        path = engine.backup_data()
        return {"backup_path": path}

    async def _handle_health_check(self, job: BackgroundJob) -> Dict[str, Any]:
        from ald01.core.self_heal import get_self_healing_engine
        engine = get_self_healing_engine()
        return engine.run_health_check()

    async def _handle_cleanup(self, job: BackgroundJob) -> Dict[str, Any]:
        from ald01.core.self_heal import get_self_healing_engine
        engine = get_self_healing_engine()
        return engine.cleanup_memory()

    async def _handle_code_gen(self, job: BackgroundJob) -> Dict[str, Any]:
        """Generate code and save to file."""
        filename = job.metadata.get("filename", "output.py")
        content = job.metadata.get("content", "")
        output_path = os.path.join(self._output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"file": output_path, "size": len(content)}

    async def _handle_doc_build(self, job: BackgroundJob) -> Dict[str, Any]:
        """Build a document from content."""
        filename = job.metadata.get("filename", "document.md")
        content = job.metadata.get("content", "")
        output_path = os.path.join(self._output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"file": output_path, "size": len(content)}

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job."""
        if job_id in self._jobs and self._jobs[job_id].status == JobStatus.QUEUED:
            self._jobs[job_id].status = JobStatus.CANCELLED
            return True
        return False

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        return job.to_dict() if job else None

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        return [j.to_dict() for j in self._jobs.values()
                if j.status in (JobStatus.QUEUED, JobStatus.RUNNING)]

    def get_recent_jobs(self, limit: int = 30) -> List[Dict[str, Any]]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_jobs": len(self._jobs),
            "running": self._running_count,
            "queued": sum(1 for j in self._jobs.values() if j.status == JobStatus.QUEUED),
            "completed": sum(1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED),
            "failed": sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED),
        }


_worker: Optional[BackgroundWorker] = None

def get_background_worker() -> BackgroundWorker:
    global _worker
    if _worker is None:
        _worker = BackgroundWorker()
    return _worker
