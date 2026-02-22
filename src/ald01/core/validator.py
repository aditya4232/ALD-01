"""
ALD-01 System Validator
Validates configuration, code, imports, and system state.
"""

import os
import sys
import time
import logging
import importlib
from typing import Any, Dict, List, Optional, Tuple

from ald01 import CONFIG_DIR, DATA_DIR, LOGS_DIR, MEMORY_DIR

logger = logging.getLogger("ald01.validator")


class ValidationResult:
    def __init__(self, name: str, passed: bool, message: str = "", details: Dict[str, Any] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "message": self.message, "details": self.details}


class SystemValidator:
    def __init__(self):
        self._results: List[ValidationResult] = []

    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        self._results = []
        for check in [self._check_python, self._check_imports, self._check_dirs, self._check_config, self._check_db]:
            try:
                r = check()
                if isinstance(r, list):
                    self._results.extend(r)
                else:
                    self._results.append(r)
            except Exception as e:
                self._results.append(ValidationResult(check.__name__, False, str(e)))
        return all(r.passed for r in self._results), self._results

    def validate_startup(self) -> bool:
        if sys.version_info < (3, 10):
            return False
        for mod in ["click", "rich", "httpx", "fastapi", "uvicorn", "yaml", "psutil"]:
            try:
                importlib.import_module(mod)
            except ImportError:
                return False
        for d in [CONFIG_DIR, DATA_DIR, LOGS_DIR, MEMORY_DIR]:
            os.makedirs(d, exist_ok=True)
        return True

    def _check_python(self) -> ValidationResult:
        v = sys.version_info
        ok = v >= (3, 10)
        return ValidationResult("Python", ok, f"{v.major}.{v.minor}.{v.micro}")

    def _check_imports(self) -> List[ValidationResult]:
        results = []
        mods = {"click": "CLI", "rich": "UI", "httpx": "HTTP", "fastapi": "API", "uvicorn": "ASGI", "yaml": "YAML", "psutil": "Sys"}
        for m, d in mods.items():
            try:
                importlib.import_module(m)
                results.append(ValidationResult(f"Import:{m}", True, d))
            except ImportError:
                results.append(ValidationResult(f"Import:{m}", False, f"{d} missing"))
        internal = [
            "ald01.config", "ald01.core.events", "ald01.core.memory", "ald01.core.tools",
            "ald01.core.orchestrator", "ald01.core.modes", "ald01.core.status",
            "ald01.core.self_heal", "ald01.core.reasoning", "ald01.core.themes",
            "ald01.core.learning", "ald01.core.tasks", "ald01.providers.base",
            "ald01.providers.openai_compat", "ald01.providers.ollama", "ald01.providers.manager",
            "ald01.agents.base", "ald01.agents.codegen", "ald01.agents.debug",
            "ald01.agents.review", "ald01.agents.security", "ald01.agents.general",
            "ald01.dashboard.server", "ald01.services.voice", "ald01.doctor.diagnostics",
            "ald01.visualization.thinking", "ald01.onboarding.wizard", "ald01.telegram.bot",
            "ald01.utils.hardware",
        ]
        for m in internal:
            try:
                importlib.import_module(m)
                results.append(ValidationResult(f"Mod:{m.replace('ald01.','')}", True, "OK"))
            except Exception as e:
                results.append(ValidationResult(f"Mod:{m.replace('ald01.','')}", False, str(e)))
        return results

    def _check_dirs(self) -> List[ValidationResult]:
        results = []
        for name, path in {"config": CONFIG_DIR, "data": DATA_DIR, "logs": LOGS_DIR, "memory": MEMORY_DIR}.items():
            ok = os.path.exists(path) or (os.makedirs(path, exist_ok=True) is None)
            results.append(ValidationResult(f"Dir:{name}", True, path))
        return results

    def _check_config(self) -> ValidationResult:
        path = os.path.join(CONFIG_DIR, "config.yaml")
        if not os.path.exists(path):
            return ValidationResult("Config", True, "Defaults")
        try:
            import yaml
            with open(path, "r") as f:
                c = yaml.safe_load(f)
            return ValidationResult("Config", isinstance(c, dict), "Valid" if isinstance(c, dict) else "Invalid")
        except Exception as e:
            return ValidationResult("Config", False, str(e))

    def _check_db(self) -> ValidationResult:
        db = os.path.join(MEMORY_DIR, "ald01.db")
        if not os.path.exists(db):
            return ValidationResult("Database", True, "Not yet created")
        try:
            import sqlite3
            conn = sqlite3.connect(db)
            r = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            return ValidationResult("Database", r and r[0] == "ok", f"Size: {os.path.getsize(db)//1024}KB")
        except Exception as e:
            return ValidationResult("Database", False, str(e))

    def get_summary(self) -> Dict[str, Any]:
        p = sum(1 for r in self._results if r.passed)
        f = sum(1 for r in self._results if not r.passed)
        return {"total": len(self._results), "passed": p, "failed": f, "all_passed": f == 0,
                "results": [r.to_dict() for r in self._results]}


_validator: Optional[SystemValidator] = None

def get_validator() -> SystemValidator:
    global _validator
    if _validator is None:
        _validator = SystemValidator()
    return _validator
