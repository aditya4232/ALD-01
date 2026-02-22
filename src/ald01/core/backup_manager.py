"""
ALD-01 Backup Manager
Automated and manual backups of conversations, config, brain state, and skills.
Supports incremental backups, compression, rotation, and restore.
"""

import os
import json
import time
import shutil
import zipfile
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR, DATA_DIR, MEMORY_DIR

logger = logging.getLogger("ald01.backup")

BACKUP_DIR = os.path.join(DATA_DIR, "backups")


class BackupManifest:
    """Tracks what was backed up and when."""

    __slots__ = ("name", "timestamp", "files", "size_bytes", "backup_type", "checksum")

    def __init__(
        self, name: str, timestamp: float, files: List[str],
        size_bytes: int, backup_type: str, checksum: str,
    ):
        self.name = name
        self.timestamp = timestamp
        self.files = files
        self.size_bytes = size_bytes
        self.backup_type = backup_type
        self.checksum = checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "files": self.files,
            "file_count": len(self.files),
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / (1024 * 1024), 2),
            "backup_type": self.backup_type,
            "checksum": self.checksum,
        }


class BackupManager:
    """
    Manages automated and manual backups for ALD-01.

    Backup types:
      - full: Everything (config, memory, brain, skills, conversations)
      - config: Config files only
      - conversations: Chat history only
      - brain: Brain state and learning data only

    Features:
      - Automatic rotation (keeps N most recent)
      - ZIP compression
      - Integrity checksums
      - Scheduled auto-backup
    """

    MAX_BACKUPS = 20
    BACKUP_TARGETS = {
        "config": [CONFIG_DIR],
        "memory": [MEMORY_DIR],
        "brain": [os.path.join(DATA_DIR, "important", "brain")],
        "skills": [os.path.join(CONFIG_DIR, "skills.json")],
        "conversations": [os.path.join(MEMORY_DIR, "conversations")],
    }

    def __init__(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self._manifest_path = os.path.join(BACKUP_DIR, "manifest.json")
        self._manifests: List[Dict[str, Any]] = []
        self._load_manifests()

    def create_backup(self, backup_type: str = "full", label: str = "") -> Dict[str, Any]:
        """
        Create a backup archive.

        Args:
            backup_type: 'full', 'config', 'conversations', or 'brain'
            label: Optional human-readable label
        """
        ts = time.time()
        dt = datetime.fromtimestamp(ts)
        name = f"ald01_{backup_type}_{dt.strftime('%Y%m%d_%H%M%S')}"
        if label:
            safe_label = "".join(c for c in label if c.isalnum() or c in "-_")[:30]
            name = f"{name}_{safe_label}"

        zip_path = os.path.join(BACKUP_DIR, f"{name}.zip")

        # Determine which directories to back up
        if backup_type == "full":
            targets = []
            for paths in self.BACKUP_TARGETS.values():
                targets.extend(paths)
        elif backup_type in self.BACKUP_TARGETS:
            targets = self.BACKUP_TARGETS[backup_type]
        else:
            return {"success": False, "error": f"Unknown backup type: {backup_type}"}

        # Create ZIP archive
        files_backed_up = []
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for target in targets:
                    if not os.path.exists(target):
                        continue

                    if os.path.isfile(target):
                        arcname = os.path.basename(target)
                        zf.write(target, arcname)
                        files_backed_up.append(arcname)
                    elif os.path.isdir(target):
                        base = os.path.basename(target)
                        for root, dirs, files in os.walk(target):
                            # Skip __pycache__ and .pyc
                            dirs[:] = [d for d in dirs if d != "__pycache__"]
                            for fname in files:
                                if fname.endswith(".pyc"):
                                    continue
                                fpath = os.path.join(root, fname)
                                arcname = os.path.join(base, os.path.relpath(fpath, target))
                                try:
                                    zf.write(fpath, arcname)
                                    files_backed_up.append(arcname)
                                except (PermissionError, OSError):
                                    continue

            # Calculate checksum
            checksum = self._file_checksum(zip_path)
            size = os.path.getsize(zip_path)

            manifest = BackupManifest(
                name=name, timestamp=ts, files=files_backed_up,
                size_bytes=size, backup_type=backup_type, checksum=checksum,
            )

            self._manifests.append(manifest.to_dict())
            self._save_manifests()
            self._rotate_backups()

            logger.info(f"Backup created: {name} ({len(files_backed_up)} files, {size} bytes)")
            return {"success": True, "backup": manifest.to_dict()}

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial zip
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return {"success": False, "error": str(e)}

    def restore_backup(self, backup_name: str) -> Dict[str, Any]:
        """Restore from a backup archive."""
        zip_path = os.path.join(BACKUP_DIR, f"{backup_name}.zip")
        if not os.path.exists(zip_path):
            return {"success": False, "error": f"Backup not found: {backup_name}"}

        # Verify integrity
        manifest = self._find_manifest(backup_name)
        if manifest:
            current_checksum = self._file_checksum(zip_path)
            if current_checksum != manifest.get("checksum"):
                return {"success": False, "error": "Backup integrity check failed"}

        # Create a pre-restore backup first
        self.create_backup("full", "pre_restore")

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Restore config files
                for member in zf.namelist():
                    if member.startswith("config/") or member.endswith(".json") or member.endswith(".yaml"):
                        target_dir = CONFIG_DIR
                    elif member.startswith("memory/") or member.startswith("conversations/"):
                        target_dir = MEMORY_DIR
                    elif member.startswith("brain/"):
                        target_dir = os.path.join(DATA_DIR, "important")
                    else:
                        target_dir = DATA_DIR

                    # Extract safely
                    extracted = zf.extract(member, target_dir)

            logger.info(f"Backup restored: {backup_name}")
            return {"success": True, "backup": backup_name}

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {"success": False, "error": str(e)}

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups, newest first."""
        # Reconcile manifests with actual files
        valid = []
        for m in self._manifests:
            zip_path = os.path.join(BACKUP_DIR, f"{m['name']}.zip")
            if os.path.exists(zip_path):
                m["size_bytes"] = os.path.getsize(zip_path)
                m["size_mb"] = round(m["size_bytes"] / (1024 * 1024), 2)
                valid.append(m)
        self._manifests = valid
        self._save_manifests()
        return sorted(valid, key=lambda x: x["timestamp"], reverse=True)

    def delete_backup(self, backup_name: str) -> bool:
        zip_path = os.path.join(BACKUP_DIR, f"{backup_name}.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        self._manifests = [m for m in self._manifests if m["name"] != backup_name]
        self._save_manifests()
        return True

    def get_stats(self) -> Dict[str, Any]:
        backups = self.list_backups()
        total_size = sum(b.get("size_bytes", 0) for b in backups)
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest": backups[-1]["datetime"] if backups else None,
            "newest": backups[0]["datetime"] if backups else None,
            "by_type": {
                t: sum(1 for b in backups if b.get("backup_type") == t)
                for t in ("full", "config", "conversations", "brain")
            },
        }

    def auto_backup_if_due(self, interval_hours: int = 6) -> Optional[Dict[str, Any]]:
        """Create auto-backup if enough time has passed since the last one."""
        backups = self.list_backups()
        if backups:
            last_ts = backups[0]["timestamp"]
            elapsed = time.time() - last_ts
            if elapsed < interval_hours * 3600:
                return None

        return self.create_backup("full", "auto")

    def _rotate_backups(self) -> None:
        """Keep only the N most recent backups."""
        backups = self.list_backups()
        if len(backups) > self.MAX_BACKUPS:
            for old in backups[self.MAX_BACKUPS:]:
                self.delete_backup(old["name"])

    def _find_manifest(self, name: str) -> Optional[Dict[str, Any]]:
        for m in self._manifests:
            if m["name"] == name:
                return m
        return None

    @staticmethod
    def _file_checksum(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def _save_manifests(self) -> None:
        try:
            with open(self._manifest_path, "w", encoding="utf-8") as f:
                json.dump(self._manifests, f, indent=2)
        except Exception as e:
            logger.warning(f"Manifest save failed: {e}")

    def _load_manifests(self) -> None:
        try:
            if os.path.exists(self._manifest_path):
                with open(self._manifest_path, encoding="utf-8") as f:
                    self._manifests = json.load(f)
        except Exception:
            self._manifests = []


_backup_mgr: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    global _backup_mgr
    if _backup_mgr is None:
        _backup_mgr = BackupManager()
    return _backup_mgr
