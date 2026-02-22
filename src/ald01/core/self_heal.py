"""
ALD-01 Self-Healing Engine
Automatic error recovery, config validation, code repair, and system health maintenance.
The brain should never break — if it does, it fixes itself.
"""

import os
import sys
import time
import json
import shutil
import asyncio
import logging
import traceback
import sqlite3
import importlib
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from functools import wraps

from ald01 import CONFIG_DIR, DATA_DIR, LOGS_DIR, MEMORY_DIR

logger = logging.getLogger("ald01.self_heal")


@dataclass
class HealingAction:
    """A self-healing action taken by the system."""
    action_type: str  # 'config_repair', 'db_repair', 'module_reload', 'fallback', 'restart'
    description: str
    success: bool
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.action_type,
            "description": self.description,
            "success": self.success,
            "timestamp": self.timestamp,
            "details": self.details,
            "error": self.error,
        }


class SelfHealingEngine:
    """
    Self-healing engine for ALD-01. Handles:
    - Configuration file corruption recovery
    - Database repair and backup
    - Module import failure recovery
    - Provider failover
    - Memory cleanup
    - Graceful degradation
    - Error pattern detection
    - Automatic retry with exponential backoff
    """

    def __init__(self):
        self._actions: List[HealingAction] = []
        self._error_counts: Dict[str, int] = {}
        self._max_retries: int = 3
        self._backoff_base: float = 1.0
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize self-healing systems."""
        self._ensure_directories()
        self._verify_config()
        self._verify_database()
        self._initialized = True
        logger.info("Self-healing engine initialized")

    # ──────────────────────────────────────────────────────────
    # Directory & File Safety
    # ──────────────────────────────────────────────────────────

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        required_dirs = [CONFIG_DIR, DATA_DIR, LOGS_DIR, MEMORY_DIR]
        for d in required_dirs:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                self._log_action("dir_create", f"Failed to create {d}", False, error=str(e))

    def _verify_config(self) -> None:
        """Verify and repair config file if needed."""
        config_path = os.path.join(CONFIG_DIR, "config.yaml")

        if not os.path.exists(config_path):
            # Config doesn't exist yet — normal for first run
            return

        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config is None:
                raise ValueError("Config file is empty")

            if not isinstance(config, dict):
                raise ValueError("Config file is not a valid YAML dictionary")

            self._log_action("config_verify", "Config file is valid", True)

        except Exception as e:
            logger.warning(f"Config file corrupted: {e}. Backing up and regenerating.")

            # Backup corrupt config
            backup_path = config_path + f".corrupt.{int(time.time())}"
            try:
                shutil.copy2(config_path, backup_path)
                self._log_action("config_backup", f"Corrupt config backed up to {backup_path}", True)
            except Exception:
                pass

            # Regenerate default config
            try:
                from ald01.config import get_config
                cfg = get_config()
                cfg.reset()
                cfg.save()
                self._log_action("config_repair", "Config regenerated from defaults", True)
            except Exception as repair_err:
                self._log_action("config_repair", "Failed to regenerate config", False, error=str(repair_err))

    def _verify_database(self) -> None:
        """Verify SQLite database integrity."""
        db_path = os.path.join(MEMORY_DIR, "ald01.db")

        if not os.path.exists(db_path):
            return  # Will be created on first use

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == "ok":
                self._log_action("db_verify", "Database integrity check passed", True)
            else:
                raise ValueError(f"Integrity check failed: {result}")

        except Exception as e:
            logger.warning(f"Database issue: {e}. Attempting repair.")

            # Backup corrupt database
            backup_path = db_path + f".corrupt.{int(time.time())}"
            try:
                shutil.copy2(db_path, backup_path)
                self._log_action("db_backup", f"Database backed up to {backup_path}", True)
            except Exception:
                pass

            # Try to repair
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("REINDEX")
                conn.execute("VACUUM")
                conn.close()
                self._log_action("db_repair", "Database repaired with REINDEX and VACUUM", True)
            except Exception:
                # Last resort: delete and recreate
                try:
                    os.remove(db_path)
                    self._log_action("db_recreate", "Database recreated (data lost)", True,
                                   details={"backup": backup_path})
                except Exception as del_err:
                    self._log_action("db_repair", "Database repair failed", False, error=str(del_err))

    # ──────────────────────────────────────────────────────────
    # Safe Execution Wrappers
    # ──────────────────────────────────────────────────────────

    def safe_execute(self, func: Callable, *args, fallback: Any = None,
                     component: str = "unknown", **kwargs) -> Any:
        """Execute a function with automatic error recovery."""
        error_key = f"{component}.{func.__name__}"

        try:
            result = func(*args, **kwargs)
            # Reset error count on success
            self._error_counts[error_key] = 0
            return result

        except Exception as e:
            self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
            count = self._error_counts[error_key]

            logger.error(f"Error in {error_key} (attempt {count}): {e}")

            # Auto-retry if under threshold
            if count <= self._max_retries:
                self._log_action(
                    "auto_retry",
                    f"Retrying {error_key} (attempt {count}/{self._max_retries})",
                    False,
                    details={"error": str(e), "traceback": traceback.format_exc()},
                )
                # Exponential backoff
                time.sleep(self._backoff_base * (2 ** (count - 1)))
                return self.safe_execute(func, *args, fallback=fallback, component=component, **kwargs)

            # Max retries exceeded — use fallback
            self._log_action(
                "fallback",
                f"Max retries exceeded for {error_key}, using fallback",
                True,
                details={"error": str(e), "attempts": count},
            )
            return fallback

    async def safe_execute_async(self, coro_func: Callable, *args, fallback: Any = None,
                                  component: str = "unknown", **kwargs) -> Any:
        """Async version of safe_execute."""
        error_key = f"{component}.{coro_func.__name__}"

        try:
            result = await coro_func(*args, **kwargs)
            self._error_counts[error_key] = 0
            return result

        except Exception as e:
            self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
            count = self._error_counts[error_key]

            logger.error(f"Async error in {error_key} (attempt {count}): {e}")

            if count <= self._max_retries:
                self._log_action(
                    "auto_retry_async",
                    f"Retrying {error_key} (attempt {count}/{self._max_retries})",
                    False,
                    details={"error": str(e)},
                )
                await asyncio.sleep(self._backoff_base * (2 ** (count - 1)))
                return await self.safe_execute_async(coro_func, *args, fallback=fallback,
                                                     component=component, **kwargs)

            self._log_action("fallback_async", f"Using fallback for {error_key}", True,
                           details={"error": str(e), "attempts": count})
            return fallback

    # ──────────────────────────────────────────────────────────
    # Circuit Breaker Pattern
    # ──────────────────────────────────────────────────────────

    def check_circuit(self, name: str) -> bool:
        """Check if a circuit breaker allows execution."""
        cb = self._circuit_breakers.get(name)
        if cb is None:
            return True

        if cb["state"] == "closed":
            return True
        elif cb["state"] == "open":
            # Check if cooldown has elapsed
            if time.time() - cb["opened_at"] > cb["cooldown_seconds"]:
                cb["state"] = "half-open"
                return True
            return False
        elif cb["state"] == "half-open":
            return True
        return True

    def record_circuit_success(self, name: str) -> None:
        """Record a success for a circuit breaker."""
        cb = self._circuit_breakers.get(name)
        if cb and cb["state"] == "half-open":
            cb["state"] = "closed"
            cb["failures"] = 0

    def record_circuit_failure(self, name: str, threshold: int = 5, cooldown: int = 60) -> None:
        """Record a failure for a circuit breaker."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = {
                "state": "closed",
                "failures": 0,
                "cooldown_seconds": cooldown,
                "opened_at": 0,
            }

        cb = self._circuit_breakers[name]
        cb["failures"] += 1

        if cb["failures"] >= threshold:
            cb["state"] = "open"
            cb["opened_at"] = time.time()
            self._log_action(
                "circuit_open",
                f"Circuit breaker '{name}' opened after {threshold} failures",
                True,
                details={"cooldown_seconds": cooldown},
            )

    # ──────────────────────────────────────────────────────────
    # Module Recovery
    # ──────────────────────────────────────────────────────────

    def safe_import(self, module_name: str, fallback_module: Optional[str] = None) -> Any:
        """Safely import a module with fallback."""
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            logger.warning(f"Failed to import {module_name}: {e}")
            self._log_action("import_fail", f"Cannot import {module_name}", False, error=str(e))

            if fallback_module:
                try:
                    return importlib.import_module(fallback_module)
                except ImportError:
                    pass

            return None

    def reload_module(self, module_name: str) -> bool:
        """Attempt to reload a module (useful for hot-fixing)."""
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                self._log_action("module_reload", f"Reloaded {module_name}", True)
                return True
            return False
        except Exception as e:
            self._log_action("module_reload", f"Failed to reload {module_name}", False, error=str(e))
            return False

    # ──────────────────────────────────────────────────────────
    # Memory & Resource Cleanup
    # ──────────────────────────────────────────────────────────

    def cleanup_memory(self) -> Dict[str, Any]:
        """Run memory cleanup to free resources."""
        import gc
        results = {}

        # Python garbage collection
        gc.collect()
        results["gc_collected"] = gc.get_count()

        # Clean old logs
        log_dir = LOGS_DIR
        if os.path.exists(log_dir):
            old_logs = []
            now = time.time()
            for f in os.listdir(log_dir):
                path = os.path.join(log_dir, f)
                if os.path.isfile(path):
                    age_days = (now - os.path.getmtime(path)) / 86400
                    if age_days > 7:  # Delete logs older than 7 days
                        try:
                            os.remove(path)
                            old_logs.append(f)
                        except Exception:
                            pass
            results["old_logs_cleaned"] = len(old_logs)

        # Compact database
        try:
            db_path = os.path.join(MEMORY_DIR, "ald01.db")
            if os.path.exists(db_path):
                db_size_before = os.path.getsize(db_path)
                conn = sqlite3.connect(db_path)
                conn.execute("VACUUM")
                conn.close()
                db_size_after = os.path.getsize(db_path)
                results["db_compacted_mb"] = round((db_size_before - db_size_after) / (1024 * 1024), 2)
        except Exception as e:
            results["db_compact_error"] = str(e)

        self._log_action("cleanup", "Memory and resource cleanup completed", True, details=results)
        return results

    def backup_data(self) -> str:
        """Create a backup of all ALD-01 data."""
        backup_dir = os.path.join(CONFIG_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"ald01_backup_{timestamp}")
        os.makedirs(backup_path, exist_ok=True)

        backed_up = []

        # Backup config
        config_path = os.path.join(CONFIG_DIR, "config.yaml")
        if os.path.exists(config_path):
            shutil.copy2(config_path, os.path.join(backup_path, "config.yaml"))
            backed_up.append("config.yaml")

        # Backup database
        db_path = os.path.join(MEMORY_DIR, "ald01.db")
        if os.path.exists(db_path):
            shutil.copy2(db_path, os.path.join(backup_path, "ald01.db"))
            backed_up.append("ald01.db")

        # Backup modes
        modes_path = os.path.join(CONFIG_DIR, "modes.json")
        if os.path.exists(modes_path):
            shutil.copy2(modes_path, os.path.join(backup_path, "modes.json"))
            backed_up.append("modes.json")

        # Backup status
        status_path = os.path.join(CONFIG_DIR, "status.json")
        if os.path.exists(status_path):
            shutil.copy2(status_path, os.path.join(backup_path, "status.json"))
            backed_up.append("status.json")

        # Backup themes
        themes_path = os.path.join(CONFIG_DIR, "themes.json")
        if os.path.exists(themes_path):
            shutil.copy2(themes_path, os.path.join(backup_path, "themes.json"))
            backed_up.append("themes.json")

        self._log_action("backup", f"Data backed up to {backup_path}", True,
                        details={"files": backed_up, "path": backup_path})

        # Clean old backups (keep last 5)
        backups = sorted(
            [d for d in os.listdir(backup_dir) if d.startswith("ald01_backup_")],
            reverse=True,
        )
        for old_backup in backups[5:]:
            try:
                shutil.rmtree(os.path.join(backup_dir, old_backup))
            except Exception:
                pass

        return backup_path

    def restore_data(self, backup_path: str) -> bool:
        """Restore data from a backup."""
        if not os.path.exists(backup_path):
            return False

        try:
            for filename in os.listdir(backup_path):
                src = os.path.join(backup_path, filename)
                if filename == "config.yaml":
                    dst = os.path.join(CONFIG_DIR, filename)
                elif filename == "ald01.db":
                    dst = os.path.join(MEMORY_DIR, filename)
                elif filename in ("modes.json", "status.json", "themes.json"):
                    dst = os.path.join(CONFIG_DIR, filename)
                else:
                    continue

                shutil.copy2(src, dst)

            self._log_action("restore", f"Data restored from {backup_path}", True)
            return True
        except Exception as e:
            self._log_action("restore", f"Restore failed: {e}", False, error=str(e))
            return False

    # ──────────────────────────────────────────────────────────
    # Error Pattern Detection
    # ──────────────────────────────────────────────────────────

    def get_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns to detect systematic issues."""
        patterns = {}
        for key, count in self._error_counts.items():
            if count > 0:
                component = key.split(".")[0]
                if component not in patterns:
                    patterns[component] = {"total_errors": 0, "functions": {}}
                patterns[component]["total_errors"] += count
                patterns[component]["functions"][key] = count

        return patterns

    def suggest_fixes(self) -> List[Dict[str, str]]:
        """Suggest fixes based on error patterns."""
        suggestions = []
        patterns = self.get_error_patterns()

        for component, data in patterns.items():
            if data["total_errors"] > 10:
                suggestions.append({
                    "component": component,
                    "severity": "high",
                    "suggestion": f"Component '{component}' has {data['total_errors']} errors. Consider checking its configuration or dependencies.",
                })
            elif data["total_errors"] > 3:
                suggestions.append({
                    "component": component,
                    "severity": "medium",
                    "suggestion": f"Component '{component}' has intermittent errors ({data['total_errors']}). Monitor for escalation.",
                })

        return suggestions

    # ──────────────────────────────────────────────────────────
    # Health Check
    # ──────────────────────────────────────────────────────────

    def run_health_check(self) -> Dict[str, Any]:
        """Run a comprehensive health check and auto-fix issues."""
        results = {
            "timestamp": time.time(),
            "checks": [],
            "fixes_applied": 0,
            "overall_healthy": True,
        }

        # Check directories
        for d in [CONFIG_DIR, DATA_DIR, LOGS_DIR, MEMORY_DIR]:
            if os.path.exists(d):
                results["checks"].append({"check": f"dir:{d}", "status": "ok"})
            else:
                os.makedirs(d, exist_ok=True)
                results["checks"].append({"check": f"dir:{d}", "status": "fixed"})
                results["fixes_applied"] += 1

        # Check database
        db_path = os.path.join(MEMORY_DIR, "ald01.db")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA integrity_check")
                conn.close()
                results["checks"].append({"check": "database", "status": "ok"})
            except Exception as e:
                results["checks"].append({"check": "database", "status": "error", "error": str(e)})
                results["overall_healthy"] = False
        else:
            results["checks"].append({"check": "database", "status": "not_created"})

        # Check config
        config_path = os.path.join(CONFIG_DIR, "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path) as f:
                    yaml.safe_load(f)
                results["checks"].append({"check": "config", "status": "ok"})
            except Exception as e:
                results["checks"].append({"check": "config", "status": "corrupt", "error": str(e)})
                self._verify_config()
                results["fixes_applied"] += 1
        else:
            results["checks"].append({"check": "config", "status": "missing"})

        # Check circuit breakers
        open_circuits = [name for name, cb in self._circuit_breakers.items() if cb["state"] == "open"]
        if open_circuits:
            results["checks"].append({"check": "circuits", "status": "open", "circuits": open_circuits})
            results["overall_healthy"] = False
        else:
            results["checks"].append({"check": "circuits", "status": "ok"})

        # Check error counts
        high_error_components = [k for k, v in self._error_counts.items() if v > 5]
        if high_error_components:
            results["checks"].append({"check": "error_rates", "status": "elevated", "components": high_error_components})
        else:
            results["checks"].append({"check": "error_rates", "status": "ok"})

        # Check disk space
        try:
            import psutil
            disk = psutil.disk_usage(os.path.expanduser("~"))
            free_gb = disk.free / (1024**3)
            if free_gb < 0.5:
                results["checks"].append({"check": "disk_space", "status": "critical", "free_gb": round(free_gb, 2)})
                results["overall_healthy"] = False
                self.cleanup_memory()
                results["fixes_applied"] += 1
            elif free_gb < 2:
                results["checks"].append({"check": "disk_space", "status": "low", "free_gb": round(free_gb, 2)})
            else:
                results["checks"].append({"check": "disk_space", "status": "ok", "free_gb": round(free_gb, 2)})
        except Exception:
            pass

        return results

    # ──────────────────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────────────────

    def _log_action(self, action_type: str, description: str, success: bool,
                    details: Dict[str, Any] = None, error: str = "") -> None:
        """Log a self-healing action."""
        action = HealingAction(
            action_type=action_type,
            description=description,
            success=success,
            details=details or {},
            error=error,
        )
        self._actions.append(action)

        # Keep history bounded
        if len(self._actions) > 500:
            self._actions = self._actions[-500:]

        level = logging.INFO if success else logging.WARNING
        logger.log(level, f"[SelfHeal] {action_type}: {description}" + (f" (error: {error})" if error else ""))

    def get_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent self-healing actions."""
        return [a.to_dict() for a in self._actions[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Get self-healing statistics."""
        return {
            "total_actions": len(self._actions),
            "success_count": sum(1 for a in self._actions if a.success),
            "failure_count": sum(1 for a in self._actions if not a.success),
            "error_counts": dict(self._error_counts),
            "circuit_breakers": {
                name: cb["state"] for name, cb in self._circuit_breakers.items()
            },
        }


# ──────────────────────────────────────────────────────────────
# Decorators for safe execution
# ──────────────────────────────────────────────────────────────

def self_healing(component: str = "unknown", fallback: Any = None):
    """Decorator to wrap a function with self-healing."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            engine = get_self_healing_engine()
            return engine.safe_execute(func, *args, fallback=fallback, component=component, **kwargs)
        return wrapper
    return decorator


def self_healing_async(component: str = "unknown", fallback: Any = None):
    """Decorator to wrap an async function with self-healing."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            engine = get_self_healing_engine()
            return await engine.safe_execute_async(func, *args, fallback=fallback, component=component, **kwargs)
        return wrapper
    return decorator


def circuit_breaker(name: str, threshold: int = 5, cooldown: int = 60):
    """Decorator to add circuit breaker pattern."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            engine = get_self_healing_engine()
            if not engine.check_circuit(name):
                logger.warning(f"Circuit '{name}' is open — skipping {func.__name__}")
                return None
            try:
                result = await func(*args, **kwargs)
                engine.record_circuit_success(name)
                return result
            except Exception as e:
                engine.record_circuit_failure(name, threshold, cooldown)
                raise
        return wrapper
    return decorator


# Singleton
_self_healing_engine: Optional[SelfHealingEngine] = None


def get_self_healing_engine() -> SelfHealingEngine:
    """Get or create the global self-healing engine."""
    global _self_healing_engine
    if _self_healing_engine is None:
        _self_healing_engine = SelfHealingEngine()
    return _self_healing_engine
