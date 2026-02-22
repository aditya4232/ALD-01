"""
ALD-01 Task Queue
Background task execution, scheduling, and job management.
Handles async tasks, recurring jobs, and priority-based execution.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappush, heappop

logger = logging.getLogger("ald01.tasks")


class TaskPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class Task:
    """Represents an executable task."""
    id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: float = 300.0
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        return self.priority.value < other.priority.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "priority": self.priority.name,
            "status": self.status.value,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round((self.completed_at - self.started_at) * 1000) if self.completed_at else 0,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class RecurringJob:
    """A recurring scheduled job."""
    id: str
    name: str
    func: Callable
    interval_seconds: float
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = field(default_factory=time.time)
    run_count: int = 0
    last_error: str = ""
    max_failures: int = 5
    consecutive_failures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
        }


class TaskQueue:
    """
    Priority-based task queue with async execution, retry logic,
    recurring jobs, and comprehensive task lifecycle management.
    """

    def __init__(self, max_concurrent: int = 5):
        self._queue: List[Task] = []  # Priority heap
        self._tasks: Dict[str, Task] = {}
        self._completed_tasks: List[Task] = []
        self._recurring_jobs: Dict[str, RecurringJob] = {}
        self._max_concurrent = max_concurrent
        self._running_count = 0
        self._running = False
        self._total_completed = 0
        self._total_failed = 0
        self._lock = asyncio.Lock()

    def submit(
        self,
        name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: float = 300.0,
        callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Submit a task for execution. Returns task ID."""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout,
            callback=callback,
            metadata=metadata or {},
        )
        heappush(self._queue, task)
        self._tasks[task_id] = task
        logger.debug(f"Task submitted: {name} (id={task_id}, priority={priority.name})")
        return task_id

    def submit_recurring(
        self,
        name: str,
        func: Callable,
        interval_seconds: float,
        *args,
        **kwargs,
    ) -> str:
        """Schedule a recurring job. Returns job ID."""
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job = RecurringJob(
            id=job_id,
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            args=args,
            kwargs=kwargs,
        )
        self._recurring_jobs[job_id] = job
        logger.info(f"Recurring job scheduled: {name} (every {interval_seconds}s)")
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a recurring job."""
        if job_id in self._recurring_jobs:
            self._recurring_jobs[job_id].enabled = False
            return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task info."""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    async def start(self) -> None:
        """Start the task queue worker."""
        self._running = True
        logger.info("Task queue started")

        # Start main worker
        asyncio.create_task(self._worker())

        # Start recurring job scheduler
        asyncio.create_task(self._recurring_scheduler())

    async def stop(self) -> None:
        """Stop the task queue."""
        self._running = False
        logger.info("Task queue stopped")

    async def _worker(self) -> None:
        """Main worker loop — processes tasks from the queue."""
        while self._running:
            try:
                if self._queue and self._running_count < self._max_concurrent:
                    async with self._lock:
                        if self._queue:
                            task = heappop(self._queue)
                            if task.status == TaskStatus.CANCELLED:
                                continue
                            asyncio.create_task(self._execute_task(task))

                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Task worker error: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task with retry and timeout logic."""
        self._running_count += 1
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        try:
            # Run with timeout
            if asyncio.iscoroutinefunction(task.func):
                task.result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout_seconds,
                )
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                task.result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: task.func(*task.args, **task.kwargs)),
                    timeout=task.timeout_seconds,
                )

            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            self._total_completed += 1

            # Run callback
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(task)
                    else:
                        task.callback(task)
                except Exception as cb_err:
                    logger.warning(f"Task callback error: {cb_err}")

        except asyncio.TimeoutError:
            task.error = f"Timeout after {task.timeout_seconds}s"
            task.status = TaskStatus.FAILED
            self._total_failed += 1

        except Exception as e:
            task.error = str(e)
            task.retry_count += 1

            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.RETRYING
                # Exponential backoff
                delay = min(2 ** task.retry_count, 60)
                logger.warning(f"Task '{task.name}' failed, retrying in {delay}s (attempt {task.retry_count}/{task.max_retries})")
                await asyncio.sleep(delay)
                heappush(self._queue, task)
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                self._total_failed += 1
                logger.error(f"Task '{task.name}' failed permanently after {task.max_retries} retries: {e}")

        finally:
            self._running_count -= 1
            # Archive completed tasks
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                self._completed_tasks.append(task)
                if len(self._completed_tasks) > 200:
                    self._completed_tasks = self._completed_tasks[-200:]

    async def _recurring_scheduler(self) -> None:
        """Check and execute due recurring jobs."""
        while self._running:
            try:
                now = time.time()
                for job in self._recurring_jobs.values():
                    if not job.enabled:
                        continue
                    if now >= job.next_run:
                        try:
                            if asyncio.iscoroutinefunction(job.func):
                                await job.func(*job.args, **job.kwargs)
                            else:
                                job.func(*job.args, **job.kwargs)

                            job.last_run = now
                            job.next_run = now + job.interval_seconds
                            job.run_count += 1
                            job.consecutive_failures = 0

                        except Exception as e:
                            job.last_error = str(e)
                            job.consecutive_failures += 1
                            job.next_run = now + job.interval_seconds

                            if job.consecutive_failures >= job.max_failures:
                                job.enabled = False
                                logger.error(f"Recurring job '{job.name}' disabled after {job.max_failures} consecutive failures")

                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Recurring scheduler error: {e}")
                await asyncio.sleep(5)

    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status."""
        return {
            "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
            "running": self._running_count,
            "completed": self._total_completed,
            "failed": self._total_failed,
            "queue_size": len(self._queue),
            "max_concurrent": self._max_concurrent,
            "recurring_jobs": len(self._recurring_jobs),
            "active_jobs": sum(1 for j in self._recurring_jobs.values() if j.enabled),
        }

    def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent task results."""
        return [t.to_dict() for t in self._completed_tasks[-limit:]]

    def get_recurring_jobs(self) -> List[Dict[str, Any]]:
        """Get all recurring jobs."""
        return [j.to_dict() for j in self._recurring_jobs.values()]


# Singleton
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get or create the global task queue."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
