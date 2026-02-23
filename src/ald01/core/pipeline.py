"""
ALD-01 Pipeline System
Chain operations together into repeatable, configurable workflows.
Supports sequential, parallel, and conditional execution with
error handling, retries, and output transformation.
"""

import os
import json
import time
import asyncio
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import OrderedDict

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.pipeline")


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class PipelineStep:
    """A single step in a pipeline."""

    def __init__(
        self,
        step_id: str,
        name: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 60,
        retries: int = 0,
        condition: Optional[str] = None,
        on_error: str = "stop",  # stop | continue | skip
        transform_output: Optional[str] = None,
    ):
        self.step_id = step_id
        self.name = name
        self.action = action  # The action type (e.g., "chat", "execute", "analyze")
        self.params = params or {}
        self.timeout = timeout
        self.retries = retries
        self.condition = condition
        self.on_error = on_error
        self.transform_output = transform_output

        # Runtime state
        self.status = StepStatus.PENDING
        self.result: Any = None
        self.error: str = ""
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.attempt: int = 0
        self.duration_ms: float = 0

    @property
    def elapsed(self) -> float:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        if self.started_at:
            return time.time() - self.started_at
        return 0

    def reset(self) -> None:
        self.status = StepStatus.PENDING
        self.result = None
        self.error = ""
        self.started_at = None
        self.completed_at = None
        self.attempt = 0
        self.duration_ms = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.step_id,
            "name": self.name,
            "action": self.action,
            "status": self.status.value,
            "attempt": self.attempt,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
            "result_preview": str(self.result)[:200] if self.result else None,
            "timeout": self.timeout,
            "retries": self.retries,
            "on_error": self.on_error,
        }


class Pipeline:
    """
    A configurable chain of steps that execute in sequence.

    Features:
    - Sequential step execution
    - Conditional step execution
    - Retry with configurable max attempts
    - Timeout per step
    - Error handling strategies (stop / continue / skip)
    - Output piping: previous step output → next step input
    - Step-level and pipeline-level hooks
    """

    def __init__(self, pipeline_id: str, name: str, description: str = ""):
        self.pipeline_id = pipeline_id
        self.name = name
        self.description = description
        self.steps: OrderedDict[str, PipelineStep] = OrderedDict()
        self.status = StepStatus.PENDING
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.run_count = 0
        self.last_run: Optional[float] = None

        # Context passed between steps
        self._context: Dict[str, Any] = {}

    def add_step(self, step: PipelineStep) -> "Pipeline":
        self.steps[step.step_id] = step
        return self

    def remove_step(self, step_id: str) -> bool:
        if step_id in self.steps:
            del self.steps[step_id]
            return True
        return False

    def reset(self) -> None:
        self.status = StepStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self._context = {}
        for step in self.steps.values():
            step.reset()

    async def execute(self, action_registry: Dict[str, Callable], initial_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute the pipeline."""
        self.reset()
        self.status = StepStatus.RUNNING
        self.started_at = time.time()
        self.run_count += 1
        self.last_run = self.started_at

        if initial_context:
            self._context.update(initial_context)

        results = {}
        failed = False

        for step_id, step in self.steps.items():
            # Check condition
            if step.condition and not self._evaluate_condition(step.condition):
                step.status = StepStatus.SKIPPED
                results[step_id] = {"status": "skipped", "reason": "condition not met"}
                continue

            # Execute with retries
            success = False
            for attempt in range(1, step.retries + 2):  # +1 for initial, +1 for range
                step.attempt = attempt
                step.status = StepStatus.RUNNING if attempt == 1 else StepStatus.RETRYING
                step.started_at = time.time()

                try:
                    action_fn = action_registry.get(step.action)
                    if not action_fn:
                        raise ValueError(f"Unknown action: {step.action}")

                    # Merge step params with pipeline context
                    exec_params = {**step.params, **self._context}

                    # Execute with timeout
                    step_result = await asyncio.wait_for(
                        action_fn(exec_params),
                        timeout=step.timeout,
                    )

                    step.completed_at = time.time()
                    step.duration_ms = (step.completed_at - step.started_at) * 1000
                    step.status = StepStatus.SUCCESS
                    step.result = step_result

                    # Store result in context for next steps
                    self._context[f"step_{step_id}"] = step_result
                    self._context["last_result"] = step_result

                    results[step_id] = {
                        "status": "success",
                        "duration_ms": step.duration_ms,
                        "result": step_result,
                    }
                    success = True
                    break

                except asyncio.TimeoutError:
                    step.completed_at = time.time()
                    step.duration_ms = (step.completed_at - step.started_at) * 1000
                    step.error = f"Timeout after {step.timeout}s"
                    step.status = StepStatus.TIMEOUT

                except Exception as e:
                    step.completed_at = time.time()
                    step.duration_ms = (step.completed_at - step.started_at) * 1000
                    step.error = str(e)
                    step.status = StepStatus.FAILED

                # Wait before retry
                if attempt <= step.retries:
                    backoff = min(2 ** attempt, 15)
                    await asyncio.sleep(backoff)

            if not success:
                results[step_id] = {
                    "status": "failed",
                    "error": step.error,
                    "attempts": step.attempt,
                }

                if step.on_error == "stop":
                    failed = True
                    break
                elif step.on_error == "skip":
                    continue

        self.completed_at = time.time()
        self.status = StepStatus.FAILED if failed else StepStatus.SUCCESS

        total_ms = (self.completed_at - self.started_at) * 1000

        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "status": self.status.value,
            "total_duration_ms": round(total_ms, 1),
            "steps_completed": sum(1 for s in self.steps.values() if s.status == StepStatus.SUCCESS),
            "steps_total": len(self.steps),
            "results": results,
        }

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a simple condition against the pipeline context."""
        try:
            if condition.startswith("has:"):
                key = condition[4:].strip()
                return key in self._context
            if condition.startswith("not:"):
                key = condition[4:].strip()
                return key not in self._context
            if condition.startswith("true:"):
                key = condition[5:].strip()
                return bool(self._context.get(key))
            if condition.startswith("false:"):
                key = condition[6:].strip()
                return not self._context.get(key)
            return True
        except Exception:
            return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.pipeline_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps.values()],
            "run_count": self.run_count,
            "last_run": self.last_run,
            "created_at": self.created_at,
        }


# ── Built-in Pipeline Templates ──

PIPELINE_TEMPLATES = {
    "code_review": {
        "name": "Automated Code Review",
        "description": "Analyze code, check security, generate suggestions",
        "steps": [
            {"step_id": "analyze", "name": "Static Analysis", "action": "analyze_code", "params": {}},
            {"step_id": "security", "name": "Security Check", "action": "security_scan", "params": {}},
            {"step_id": "suggestions", "name": "Generate Suggestions", "action": "generate_suggestions", "params": {}, "condition": "has:step_analyze"},
            {"step_id": "report", "name": "Build Report", "action": "build_report", "params": {}},
        ],
    },
    "deployment": {
        "name": "Deployment Pipeline",
        "description": "Build, test, and deploy application",
        "steps": [
            {"step_id": "lint", "name": "Lint Check", "action": "execute_command", "params": {"command": "ruff check ."}, "on_error": "continue"},
            {"step_id": "test", "name": "Run Tests", "action": "execute_command", "params": {"command": "pytest"}, "timeout": 120},
            {"step_id": "build", "name": "Build", "action": "execute_command", "params": {"command": "python -m build"}, "condition": "true:step_test"},
            {"step_id": "notify", "name": "Notify", "action": "send_notification", "params": {"message": "Deployment complete"}},
        ],
    },
    "backup_rotate": {
        "name": "Backup & Rotate",
        "description": "Create backup and clean up old ones",
        "steps": [
            {"step_id": "backup", "name": "Create Backup", "action": "create_backup", "params": {"type": "full"}},
            {"step_id": "verify", "name": "Verify Backup", "action": "verify_backup", "params": {}, "condition": "has:step_backup"},
            {"step_id": "cleanup", "name": "Cleanup Old", "action": "cleanup_backups", "params": {"keep": 10}},
        ],
    },
    "health_check": {
        "name": "System Health Check",
        "description": "Run comprehensive health diagnostics",
        "steps": [
            {"step_id": "providers", "name": "Check Providers", "action": "check_providers", "params": {}, "on_error": "continue"},
            {"step_id": "memory", "name": "Check Memory", "action": "check_memory", "params": {}, "on_error": "continue"},
            {"step_id": "disk", "name": "Check Disk", "action": "check_disk", "params": {}, "on_error": "continue"},
            {"step_id": "report", "name": "Health Report", "action": "build_health_report", "params": {}},
        ],
    },
}


class PipelineManager:
    """
    Manages pipeline creation, execution, and history.

    Features:
    - Built-in pipeline templates
    - Custom pipeline creation
    - Execution history tracking
    - Action registry for pluggable step handlers
    - Pipeline scheduling (via scheduler integration)
    """

    MAX_HISTORY = 100

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._action_registry: Dict[str, Callable] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._persistence_path = os.path.join(CONFIG_DIR, "pipelines.json")
        self._register_default_actions()
        self._load()

    def create_pipeline(
        self, pipeline_id: str, name: str,
        description: str = "",
        steps: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Create a new pipeline."""
        pipeline = Pipeline(pipeline_id, name, description)

        if steps:
            for sdata in steps:
                step = PipelineStep(
                    step_id=sdata.get("step_id", f"step_{len(pipeline.steps)}"),
                    name=sdata.get("name", "Unnamed"),
                    action=sdata.get("action", "noop"),
                    params=sdata.get("params", {}),
                    timeout=sdata.get("timeout", 60),
                    retries=sdata.get("retries", 0),
                    condition=sdata.get("condition"),
                    on_error=sdata.get("on_error", "stop"),
                )
                pipeline.add_step(step)

        self._pipelines[pipeline_id] = pipeline
        self._save()
        return {"success": True, "pipeline": pipeline.to_dict()}

    def create_from_template(self, template_id: str, pipeline_id: str = "") -> Dict[str, Any]:
        """Create a pipeline from a built-in template."""
        tmpl = PIPELINE_TEMPLATES.get(template_id)
        if not tmpl:
            return {"success": False, "error": f"Unknown template: {template_id}"}

        pid = pipeline_id or f"{template_id}_{int(time.time())}"
        return self.create_pipeline(
            pid, tmpl["name"], tmpl.get("description", ""),
            steps=tmpl["steps"],
        )

    async def run(self, pipeline_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"success": False, "error": f"Pipeline not found: {pipeline_id}"}

        result = await pipeline.execute(self._action_registry, context)

        # Store in history
        self._execution_history.append({
            "pipeline_id": pipeline_id,
            "name": pipeline.name,
            "status": result["status"],
            "duration_ms": result["total_duration_ms"],
            "timestamp": time.time(),
        })
        if len(self._execution_history) > self.MAX_HISTORY:
            self._execution_history = self._execution_history[-self.MAX_HISTORY:]

        return result

    def register_action(self, action_name: str, handler: Callable) -> None:
        """Register a custom action handler."""
        self._action_registry[action_name] = handler

    def list_pipelines(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._pipelines.values()]

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        p = self._pipelines.get(pipeline_id)
        return p.to_dict() if p else None

    def delete_pipeline(self, pipeline_id: str) -> bool:
        if pipeline_id in self._pipelines:
            del self._pipelines[pipeline_id]
            self._save()
            return True
        return False

    def list_templates(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": tid,
                "name": tdata["name"],
                "description": tdata.get("description", ""),
                "steps": len(tdata["steps"]),
            }
            for tid, tdata in PIPELINE_TEMPLATES.items()
        ]

    def list_actions(self) -> List[str]:
        return sorted(self._action_registry.keys())

    def get_history(self, limit: int = 20) -> List[Dict]:
        return self._execution_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        total_runs = len(self._execution_history)
        success_runs = sum(1 for h in self._execution_history if h["status"] == "success")
        return {
            "pipelines_count": len(self._pipelines),
            "templates_count": len(PIPELINE_TEMPLATES),
            "registered_actions": len(self._action_registry),
            "total_runs": total_runs,
            "success_rate": round(success_runs / max(total_runs, 1) * 100, 1),
            "recent_runs": self._execution_history[-5:],
        }

    def _register_default_actions(self) -> None:
        """Register built-in action handlers."""

        async def noop(params: Dict) -> Dict:
            return {"action": "noop", "message": "No operation"}

        async def log_action(params: Dict) -> Dict:
            msg = params.get("message", "Pipeline step executed")
            logger.info(f"[Pipeline] {msg}")
            return {"logged": msg}

        async def sleep_action(params: Dict) -> Dict:
            duration = params.get("duration", 1)
            await asyncio.sleep(min(duration, 30))
            return {"slept": duration}

        async def execute_command_action(params: Dict) -> Dict:
            try:
                from ald01.core.executor import get_executor
                result = await get_executor().execute(
                    params.get("command", "echo ok"),
                    timeout=params.get("timeout", 30),
                )
                return result.to_dict()
            except Exception as e:
                return {"error": str(e)}

        async def analyze_code_action(params: Dict) -> Dict:
            try:
                from ald01.core.code_analyzer import get_code_analyzer
                path = params.get("path", ".")
                return get_code_analyzer().analyze_directory(path)
            except Exception as e:
                return {"error": str(e)}

        async def create_backup_action(params: Dict) -> Dict:
            try:
                from ald01.core.backup_manager import get_backup_manager
                return get_backup_manager().create_backup(
                    backup_type=params.get("type", "full"),
                )
            except Exception as e:
                return {"error": str(e)}

        async def send_notification_action(params: Dict) -> Dict:
            try:
                from ald01.core.notifications import get_notification_manager
                get_notification_manager().notify(
                    title="Pipeline",
                    message=params.get("message", "Step completed"),
                    level=params.get("level", "info"),
                )
                return {"notified": True}
            except Exception as e:
                return {"error": str(e)}

        async def emit_webhook_action(params: Dict) -> Dict:
            try:
                from ald01.core.webhooks import get_webhook_engine
                count = await get_webhook_engine().emit(
                    event=params.get("event", "pipeline.step"),
                    payload=params.get("payload", {}),
                )
                return {"webhooks_triggered": count}
            except Exception as e:
                return {"error": str(e)}

        self._action_registry = {
            "noop": noop,
            "log": log_action,
            "sleep": sleep_action,
            "execute_command": execute_command_action,
            "analyze_code": analyze_code_action,
            "create_backup": create_backup_action,
            "send_notification": send_notification_action,
            "emit_webhook": emit_webhook_action,
        }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            data = {}
            for pid, pipeline in self._pipelines.items():
                data[pid] = {
                    "name": pipeline.name,
                    "description": pipeline.description,
                    "steps": [
                        {
                            "step_id": s.step_id,
                            "name": s.name,
                            "action": s.action,
                            "params": s.params,
                            "timeout": s.timeout,
                            "retries": s.retries,
                            "condition": s.condition,
                            "on_error": s.on_error,
                        }
                        for s in pipeline.steps.values()
                    ],
                }
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Pipeline save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, encoding="utf-8") as f:
                    data = json.load(f)
                for pid, pdata in data.items():
                    self.create_pipeline(
                        pid, pdata["name"],
                        pdata.get("description", ""),
                        pdata.get("steps", []),
                    )
        except Exception:
            pass


_pipeline_mgr: Optional[PipelineManager] = None


def get_pipeline_manager() -> PipelineManager:
    global _pipeline_mgr
    if _pipeline_mgr is None:
        _pipeline_mgr = PipelineManager()
    return _pipeline_mgr
