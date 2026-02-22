"""
ALD-01 Data Manager
Categorized user data storage with reset capabilities.
All user data in one folder: important, non-important, and temp.
"""

import os
import time
import json
import shutil
import logging
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR, DATA_DIR

logger = logging.getLogger("ald01.data_manager")


class DataCategory:
    IMPORTANT = "important"    # Config, brain state, learning data — never auto-deleted
    NORMAL = "normal"          # Conversation history, logs, mode history
    TEMP = "temp"              # Cache, temp files, worker output
    BACKUP = "backups"         # System backups


class DataManager:
    """
    Manages all user data in categorized folders.
    
    Structure:
    ~/.ald01/data/
        important/    — Brain state, learning data, skills, user profile
        normal/       — Conversations, session data, mode history
        temp/         — Cache, temporary files, worker output
        backups/      — System backups
    """

    def __init__(self):
        self._base_dir = DATA_DIR
        self._categories = {
            DataCategory.IMPORTANT: os.path.join(self._base_dir, "important"),
            DataCategory.NORMAL: os.path.join(self._base_dir, "normal"),
            DataCategory.TEMP: os.path.join(self._base_dir, "temp"),
            DataCategory.BACKUP: os.path.join(self._base_dir, "backups"),
        }
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for path in self._categories.values():
            os.makedirs(path, exist_ok=True)

    def get_path(self, category: str, filename: str = "") -> str:
        """Get the path for a data file in a category."""
        base = self._categories.get(category, self._categories[DataCategory.NORMAL])
        if filename:
            return os.path.join(base, filename)
        return base

    def save(self, category: str, filename: str, data: Any) -> str:
        """Save data to a categorized file."""
        path = self.get_path(category, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if filename.endswith(".json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(data))

        return path

    def load(self, category: str, filename: str, default: Any = None) -> Any:
        """Load data from a categorized file."""
        path = self.get_path(category, filename)
        if not os.path.exists(path):
            return default

        try:
            if filename.endswith(".json"):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to load {path}: {e}")
            return default

    def delete(self, category: str, filename: str) -> bool:
        """Delete a specific file."""
        path = self.get_path(category, filename)
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")
        return False

    def reset_category(self, category: str) -> Dict[str, Any]:
        """Reset (delete all files in) a category."""
        path = self._categories.get(category)
        if not path or category == DataCategory.IMPORTANT:
            return {"error": "Cannot reset important data. Use reset_important() explicitly."}

        count = 0
        try:
            if os.path.exists(path):
                for f in os.listdir(path):
                    fp = os.path.join(path, f)
                    if os.path.isfile(fp):
                        os.remove(fp)
                        count += 1
                    elif os.path.isdir(fp):
                        shutil.rmtree(fp)
                        count += 1
        except Exception as e:
            return {"error": str(e), "deleted": count}

        return {"category": category, "deleted": count}

    def reset_temp(self) -> Dict[str, Any]:
        """Reset temp data — safe, no important data lost."""
        return self.reset_category(DataCategory.TEMP)

    def reset_normal(self) -> Dict[str, Any]:
        """Reset normal data — conversations, mode history, etc."""
        return self.reset_category(DataCategory.NORMAL)

    def reset_important(self, confirm: str = "") -> Dict[str, Any]:
        """Reset important data — REQUIRES confirmation string."""
        if confirm != "I_CONFIRM_RESET":
            return {"error": "Must pass confirm='I_CONFIRM_RESET' to reset important data"}
        return self.reset_category(DataCategory.IMPORTANT)

    def reset_all(self, confirm: str = "") -> Dict[str, Any]:
        """Reset ALL data — REQUIRES confirmation."""
        if confirm != "I_CONFIRM_RESET_ALL":
            return {"error": "Must pass confirm='I_CONFIRM_RESET_ALL'"}
        results = {}
        for cat in [DataCategory.TEMP, DataCategory.NORMAL, DataCategory.IMPORTANT]:
            results[cat] = self.reset_category(cat)
        return results

    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage usage by category."""
        info = {}
        total = 0
        for cat, path in self._categories.items():
            if not os.path.exists(path):
                info[cat] = {"files": 0, "size_kb": 0}
                continue
            files = 0
            size = 0
            for root, dirs, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(root, f)
                    files += 1
                    size += os.path.getsize(fp)
            info[cat] = {"files": files, "size_kb": round(size / 1024, 1)}
            total += size
        info["total_size_kb"] = round(total / 1024, 1)
        info["total_size_mb"] = round(total / (1024 * 1024), 2)
        return info

    def list_files(self, category: str) -> List[Dict[str, Any]]:
        """List files in a category."""
        path = self._categories.get(category)
        if not path or not os.path.exists(path):
            return []

        files = []
        for f in sorted(os.listdir(path)):
            fp = os.path.join(path, f)
            if os.path.isfile(fp):
                files.append({
                    "name": f,
                    "size_kb": round(os.path.getsize(fp) / 1024, 1),
                    "modified": os.path.getmtime(fp),
                    "category": category,
                })
        return files


_data_manager: Optional[DataManager] = None

def get_data_manager() -> DataManager:
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager
