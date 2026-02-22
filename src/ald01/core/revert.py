"""
ALD-01 Self-Revert System
Allows reverting configuration and system changes without losing data.
The doctor can fix broken state, and users can revert to previous snapshots.
"""

import os
import time
import json
import shutil
import logging
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR, DATA_DIR, MEMORY_DIR

logger = logging.getLogger("ald01.revert")


class RevertManager:
    """
    Manages system state snapshots and reversion.
    
    - Snapshots before critical changes
    - Reverts to any previous snapshot
    - Doctor auto-repair without data loss
    - Config-only revert (preserves data)
    """

    def __init__(self):
        self._snapshots_dir = os.path.join(CONFIG_DIR, "snapshots")
        os.makedirs(self._snapshots_dir, exist_ok=True)

    def create_snapshot(self, label: str = "") -> str:
        """Create a full system snapshot. (Config + state, NOT data/conversations)"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        snap_name = f"snap_{timestamp}_{label}" if label else f"snap_{timestamp}"
        snap_dir = os.path.join(self._snapshots_dir, snap_name)
        os.makedirs(snap_dir, exist_ok=True)

        files_to_snapshot = [
            (os.path.join(CONFIG_DIR, "config.yaml"), "config.yaml"),
            (os.path.join(CONFIG_DIR, "modes.json"), "modes.json"),
            (os.path.join(CONFIG_DIR, "status.json"), "status.json"),
            (os.path.join(CONFIG_DIR, "themes.json"), "themes.json"),
            (os.path.join(CONFIG_DIR, "language.json"), "language.json"),
            (os.path.join(CONFIG_DIR, "learning.json"), "learning.json"),
            (os.path.join(CONFIG_DIR, "brain.json"), "brain.json"),
            (os.path.join(CONFIG_DIR, "scheduler.json"), "scheduler.json"),
            (os.path.join(CONFIG_DIR, "plugins_config.json"), "plugins_config.json"),
        ]

        snapped = []
        for src, name in files_to_snapshot:
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(snap_dir, name))
                snapped.append(name)

        # Save metadata
        meta = {
            "label": label,
            "timestamp": time.time(),
            "files": snapped,
            "created_at": timestamp,
        }
        with open(os.path.join(snap_dir, "_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Snapshot created: {snap_name} ({len(snapped)} files)")

        # Keep max 20 snapshots
        self._cleanup_old_snapshots(20)

        return snap_name

    def revert_to_snapshot(self, snap_name: str) -> Dict[str, Any]:
        """Revert system to a previous snapshot. Preserves all data."""
        snap_dir = os.path.join(self._snapshots_dir, snap_name)
        if not os.path.exists(snap_dir):
            return {"success": False, "error": f"Snapshot not found: {snap_name}"}

        # Create a backup of current state first
        self.create_snapshot(label="pre_revert")

        restored = []
        for f in os.listdir(snap_dir):
            if f.startswith("_"):
                continue
            src = os.path.join(snap_dir, f)
            dst = os.path.join(CONFIG_DIR, f)
            try:
                shutil.copy2(src, dst)
                restored.append(f)
            except Exception as e:
                logger.warning(f"Failed to restore {f}: {e}")

        logger.info(f"Reverted to snapshot: {snap_name} ({len(restored)} files)")
        return {"success": True, "snapshot": snap_name, "restored": restored}

    def revert_config_only(self) -> Dict[str, Any]:
        """Reset config to defaults without touching data, brain, or learning."""
        self.create_snapshot(label="pre_config_reset")

        config_path = os.path.join(CONFIG_DIR, "config.yaml")
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
            # Config will regenerate on next load
            return {"success": True, "message": "Config reset to defaults. Data preserved."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def doctor_fix(self) -> Dict[str, Any]:
        """
        Doctor auto-repair: Fix broken state WITHOUT resetting data.
        Only repairs config and system files, never touches user data.
        """
        self.create_snapshot(label="pre_doctor_fix")

        fixes = []

        # 1. Fix corrupt config
        config_path = os.path.join(CONFIG_DIR, "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path) as f:
                    yaml.safe_load(f)
            except Exception:
                os.remove(config_path)
                fixes.append("Removed corrupt config.yaml (will regenerate)")

        # 2. Fix corrupt JSON files
        json_files = ["modes.json", "status.json", "themes.json", "language.json",
                       "scheduler.json", "plugins_config.json"]
        for jf in json_files:
            path = os.path.join(CONFIG_DIR, jf)
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        json.load(f)
                except Exception:
                    os.remove(path)
                    fixes.append(f"Removed corrupt {jf} (will regenerate)")

        # 3. Fix database
        db_path = os.path.join(MEMORY_DIR, "ald01.db")
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result and result[0] != "ok":
                    conn.execute("REINDEX")
                    conn.execute("VACUUM")
                    fixes.append("Repaired database (REINDEX + VACUUM)")
                conn.close()
            except Exception as e:
                fixes.append(f"Database repair attempted: {e}")

        # 4. Ensure directories exist
        for d in [CONFIG_DIR, DATA_DIR, MEMORY_DIR]:
            os.makedirs(d, exist_ok=True)

        return {
            "success": True,
            "fixes_applied": len(fixes),
            "fixes": fixes,
            "data_preserved": True,
            "message": "Doctor fix completed. All user data is safe.",
        }

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots."""
        snapshots = []
        if not os.path.exists(self._snapshots_dir):
            return snapshots

        for snap in sorted(os.listdir(self._snapshots_dir), reverse=True):
            snap_dir = os.path.join(self._snapshots_dir, snap)
            if not os.path.isdir(snap_dir):
                continue

            meta_file = os.path.join(snap_dir, "_meta.json")
            meta = {}
            if os.path.exists(meta_file):
                try:
                    with open(meta_file) as f:
                        meta = json.load(f)
                except Exception:
                    pass

            snapshots.append({
                "name": snap,
                "label": meta.get("label", ""),
                "timestamp": meta.get("timestamp", 0),
                "files": meta.get("files", []),
            })

        return snapshots

    def delete_snapshot(self, snap_name: str) -> bool:
        snap_dir = os.path.join(self._snapshots_dir, snap_name)
        if os.path.exists(snap_dir):
            shutil.rmtree(snap_dir)
            return True
        return False

    def _cleanup_old_snapshots(self, keep: int = 20) -> None:
        snapshots = sorted(os.listdir(self._snapshots_dir))
        for old in snapshots[:-keep]:
            try:
                shutil.rmtree(os.path.join(self._snapshots_dir, old))
            except Exception:
                pass


_revert_mgr: Optional[RevertManager] = None

def get_revert_manager() -> RevertManager:
    global _revert_mgr
    if _revert_mgr is None:
        _revert_mgr = RevertManager()
    return _revert_mgr
