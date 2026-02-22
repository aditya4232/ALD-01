"""
ALD-01 Command Executor
Sandboxed command execution for the terminal page.
Supports streaming output, timeouts, working directory management,
command history, and safety controls.
"""

import os
import re
import time
import asyncio
import logging
import shlex
from collections import deque
from typing import Any, AsyncGenerator, Deque, Dict, List, Optional

logger = logging.getLogger("ald01.executor")


# Commands that are NEVER allowed
BLOCKED_COMMANDS = frozenset({
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
    ":(){ :|:& };:", "format c:", "del /s /q c:\\",
    "shutdown", "reboot", "halt", "poweroff",
})

# Patterns that indicate dangerous operations
DANGER_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/[^.]"),
    re.compile(r"format\s+[a-zA-Z]:"),
    re.compile(r"del\s+/[sq]\s+[a-zA-Z]:\\"),
    re.compile(r"mkfs\.\w+\s+/dev/"),
    re.compile(r"dd\s+if=/dev/zero"),
    re.compile(r">\s*/dev/sd[a-z]"),
]

# Maximum concurrent processes
MAX_CONCURRENT = 5

# Maximum output buffer per process (characters)
MAX_OUTPUT_SIZE = 500_000


class CommandResult:
    """Result of a completed command execution."""

    __slots__ = (
        "command", "exit_code", "stdout", "stderr",
        "started_at", "finished_at", "duration_ms",
        "working_dir", "was_killed",
    )

    def __init__(self):
        self.command: str = ""
        self.exit_code: int = -1
        self.stdout: str = ""
        self.stderr: str = ""
        self.started_at: float = 0
        self.finished_at: float = 0
        self.duration_ms: float = 0
        self.working_dir: str = ""
        self.was_killed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout[-10_000:],  # Last 10K chars
            "stderr": self.stderr[-5_000:],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": round(self.duration_ms, 1),
            "working_dir": self.working_dir,
            "was_killed": self.was_killed,
            "success": self.exit_code == 0,
        }


class RunningProcess:
    """Wraps an active subprocess for tracking."""

    def __init__(self, proc: asyncio.subprocess.Process, command: str, cwd: str):
        self.proc = proc
        self.command = command
        self.cwd = cwd
        self.started_at = time.time()
        self.output_buffer: List[str] = []
        self.output_size = 0

    @property
    def pid(self) -> Optional[int]:
        return self.proc.pid

    @property
    def runtime_seconds(self) -> float:
        return time.time() - self.started_at


class CommandExecutor:
    """
    Safe command executor with sandboxing, streaming, and history.

    Safety features:
    - Blocked command list
    - Dangerous pattern detection
    - Timeout enforcement
    - Output size limits
    - Concurrent process limits
    - Working directory validation
    """

    DEFAULT_TIMEOUT = 30
    MAX_HISTORY = 200

    def __init__(self, default_cwd: Optional[str] = None):
        self._default_cwd = default_cwd or os.path.expanduser("~")
        self._history: Deque[Dict[str, Any]] = deque(maxlen=self.MAX_HISTORY)
        self._running: Dict[int, RunningProcess] = {}
        self._aliases: Dict[str, str] = {
            "ll": "ls -la",
            "cls": "clear",
            "la": "ls -la",
            "..": "cd ..",
        }

    def validate_command(self, command: str) -> Dict[str, Any]:
        """Check if a command is safe to execute."""
        cmd_lower = command.strip().lower()

        # Check blocked list
        for blocked in BLOCKED_COMMANDS:
            if cmd_lower.startswith(blocked):
                return {
                    "safe": False,
                    "reason": f"Blocked command: {blocked}",
                    "severity": "critical",
                }

        # Check dangerous patterns
        for pattern in DANGER_PATTERNS:
            if pattern.search(command):
                return {
                    "safe": False,
                    "reason": f"Matches dangerous pattern: {pattern.pattern}",
                    "severity": "high",
                }

        # Check concurrent limit
        if len(self._running) >= MAX_CONCURRENT:
            return {
                "safe": False,
                "reason": f"Too many running processes ({MAX_CONCURRENT} max)",
                "severity": "medium",
            }

        return {"safe": True}

    async def execute(
        self, command: str, cwd: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT, env: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        """Execute a command and return the result."""
        result = CommandResult()
        result.command = command
        result.working_dir = cwd or self._default_cwd

        # Apply aliases
        first_word = command.split()[0] if command.strip() else ""
        if first_word in self._aliases:
            command = command.replace(first_word, self._aliases[first_word], 1)

        # Validate
        validation = self.validate_command(command)
        if not validation["safe"]:
            result.stderr = f"Command blocked: {validation['reason']}"
            result.exit_code = 126
            self._add_to_history(result)
            return result

        # Validate working directory
        work_dir = cwd or self._default_cwd
        if not os.path.isdir(work_dir):
            work_dir = os.path.expanduser("~")

        # Prepare environment
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)
        # Force non-interactive
        proc_env["TERM"] = "dumb"

        result.started_at = time.time()

        try:
            # Use shell on Windows, exec on Unix
            if os.name == "nt":
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=work_dir,
                    env=proc_env,
                )
            else:
                args = shlex.split(command)
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=work_dir,
                    env=proc_env,
                )

            rp = RunningProcess(proc, command, work_dir)
            if proc.pid:
                self._running[proc.pid] = rp

            try:
                stdout_raw, stderr_raw = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout,
                )
                result.stdout = stdout_raw.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                result.stderr = stderr_raw.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE // 2]
                result.exit_code = proc.returncode or 0

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                result.stderr = f"Command timed out after {timeout}s"
                result.exit_code = 124
                result.was_killed = True

            finally:
                if proc.pid and proc.pid in self._running:
                    del self._running[proc.pid]

        except FileNotFoundError:
            result.stderr = f"Command not found: {command.split()[0]}"
            result.exit_code = 127
        except PermissionError:
            result.stderr = "Permission denied"
            result.exit_code = 126
        except Exception as e:
            result.stderr = f"Execution error: {str(e)}"
            result.exit_code = 1

        result.finished_at = time.time()
        result.duration_ms = (result.finished_at - result.started_at) * 1000

        self._add_to_history(result)
        return result

    async def stream_execute(
        self, command: str, cwd: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> AsyncGenerator[str, None]:
        """Execute a command and stream output line by line."""
        validation = self.validate_command(command)
        if not validation["safe"]:
            yield f"ERROR: {validation['reason']}\n"
            return

        work_dir = cwd or self._default_cwd
        if not os.path.isdir(work_dir):
            work_dir = os.path.expanduser("~")

        env = os.environ.copy()
        env["TERM"] = "dumb"

        try:
            if os.name == "nt":
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=work_dir,
                    env=env,
                )
            else:
                args = shlex.split(command)
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=work_dir,
                    env=env,
                )

            rp = RunningProcess(proc, command, work_dir)
            if proc.pid:
                self._running[proc.pid] = rp

            total_size = 0
            try:
                async def read_with_timeout():
                    return await asyncio.wait_for(
                        proc.stdout.readline(), timeout=timeout,
                    )

                while True:
                    try:
                        line = await read_with_timeout()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="replace")
                        total_size += len(decoded)
                        if total_size > MAX_OUTPUT_SIZE:
                            yield "\n[OUTPUT TRUNCATED]\n"
                            proc.kill()
                            break
                        yield decoded
                    except asyncio.TimeoutError:
                        yield f"\n[TIMEOUT after {timeout}s]\n"
                        proc.kill()
                        break

                await proc.wait()

            finally:
                if proc.pid and proc.pid in self._running:
                    del self._running[proc.pid]

        except FileNotFoundError:
            yield f"Command not found: {command.split()[0]}\n"
        except Exception as e:
            yield f"Error: {str(e)}\n"

    async def kill_process(self, pid: int) -> bool:
        """Kill a running process by PID."""
        rp = self._running.get(pid)
        if rp:
            try:
                rp.proc.kill()
                await rp.proc.wait()
                del self._running[pid]
                return True
            except Exception:
                pass
        return False

    def get_running(self) -> List[Dict[str, Any]]:
        return [
            {
                "pid": pid,
                "command": rp.command,
                "cwd": rp.cwd,
                "runtime_seconds": round(rp.runtime_seconds, 1),
            }
            for pid, rp in self._running.items()
        ]

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        items = list(self._history)
        return items[-limit:]

    def clear_history(self) -> None:
        self._history.clear()

    def set_alias(self, name: str, command: str) -> None:
        self._aliases[name] = command

    def get_aliases(self) -> Dict[str, str]:
        return dict(self._aliases)

    def set_default_cwd(self, path: str) -> bool:
        if os.path.isdir(path):
            self._default_cwd = path
            return True
        return False

    def _add_to_history(self, result: CommandResult) -> None:
        self._history.append(result.to_dict())


_executor: Optional[CommandExecutor] = None


def get_executor() -> CommandExecutor:
    global _executor
    if _executor is None:
        _executor = CommandExecutor()
    return _executor
