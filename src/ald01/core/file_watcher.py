"""
ALD-01 File Watcher
Monitors directories for changes (created, modified, deleted) and
emits events for the dashboard and background worker to act on.
Uses polling-based approach for cross-platform compatibility.
"""

import os
import time
import asyncio
import logging
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("ald01.watcher")


class FileEvent:
    """Represents a file system change event."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"

    __slots__ = ("event_type", "path", "old_path", "timestamp", "size", "is_dir")

    def __init__(
        self, event_type: str, path: str, old_path: str = "",
        size: int = 0, is_dir: bool = False,
    ):
        self.event_type = event_type
        self.path = path
        self.old_path = old_path
        self.timestamp = time.time()
        self.size = size
        self.is_dir = is_dir

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "path": self.path,
            "old_path": self.old_path,
            "timestamp": self.timestamp,
            "size": self.size,
            "is_dir": self.is_dir,
        }


class FileSnapshot:
    """Snapshot of a directory's state at a point in time."""

    def __init__(self):
        self.files: Dict[str, Dict[str, Any]] = {}  # path -> {mtime, size, hash}

    def scan(self, directory: str, extensions: Optional[Set[str]] = None,
             ignore_patterns: Optional[List[str]] = None) -> None:
        """Scan directory and record file states."""
        self.files.clear()
        ignore = set(ignore_patterns or [])
        ignore.update({"__pycache__", ".git", "node_modules", ".venv", "venv", ".mypy_cache"})

        try:
            for root, dirs, files in os.walk(directory):
                # Filter ignored directories
                dirs[:] = [d for d in dirs if d not in ignore]

                for fname in files:
                    if extensions and not any(fname.endswith(f".{ext}") for ext in extensions):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        stat = os.stat(fpath)
                        self.files[fpath] = {
                            "mtime": stat.st_mtime,
                            "size": stat.st_size,
                        }
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError) as e:
            logger.warning(f"Directory scan failed for {directory}: {e}")


class WatchTarget:
    """A directory being monitored."""

    def __init__(
        self, directory: str, extensions: Optional[Set[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        recursive: bool = True, label: str = "",
    ):
        self.directory = os.path.abspath(directory)
        self.extensions = extensions
        self.ignore_patterns = ignore_patterns or []
        self.recursive = recursive
        self.label = label or os.path.basename(directory)
        self.snapshot = FileSnapshot()
        self.event_count = 0
        self.last_event: Optional[FileEvent] = None

    def take_snapshot(self) -> None:
        self.snapshot.scan(self.directory, self.extensions, self.ignore_patterns)

    def detect_changes(self) -> List[FileEvent]:
        """Compare current state with snapshot and return events."""
        old_files = dict(self.snapshot.files)
        new_snapshot = FileSnapshot()
        new_snapshot.scan(self.directory, self.extensions, self.ignore_patterns)

        events: List[FileEvent] = []

        # Detect new and modified files
        for fpath, new_info in new_snapshot.files.items():
            if fpath not in old_files:
                events.append(FileEvent(
                    FileEvent.CREATED, fpath, size=new_info["size"],
                ))
            elif new_info["mtime"] != old_files[fpath]["mtime"]:
                events.append(FileEvent(
                    FileEvent.MODIFIED, fpath, size=new_info["size"],
                ))

        # Detect deleted files
        for fpath in old_files:
            if fpath not in new_snapshot.files:
                events.append(FileEvent(
                    FileEvent.DELETED, fpath,
                ))

        # Update snapshot
        self.snapshot = new_snapshot
        self.event_count += len(events)
        if events:
            self.last_event = events[-1]

        return events


class FileWatcher:
    """
    Cross-platform file watcher using polling.

    Features:
    - Watch multiple directories
    - Extension filtering
    - Ignore patterns
    - Callback-based event handling
    - Debouncing (coalesce rapid changes)
    - Event history
    - WebSocket-ready event emission
    """

    DEFAULT_INTERVAL = 2.0  # seconds between polls
    MAX_EVENTS = 500

    def __init__(self, poll_interval: float = DEFAULT_INTERVAL):
        self._targets: Dict[str, WatchTarget] = {}
        self._callbacks: List[Callable] = []
        self._event_history: List[Dict[str, Any]] = []
        self._poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._debounce_buffer: Dict[str, float] = {}
        self._debounce_ms = 500  # Ignore events within 500ms of each other for same file

    def watch(
        self, directory: str, extensions: Optional[Set[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        recursive: bool = True, label: str = "",
    ) -> bool:
        """Add a directory to watch."""
        directory = os.path.abspath(directory)
        if not os.path.isdir(directory):
            logger.warning(f"Cannot watch non-existent directory: {directory}")
            return False

        target = WatchTarget(directory, extensions, ignore_patterns, recursive, label)
        target.take_snapshot()
        self._targets[directory] = target
        logger.info(f"Watching: {directory} ({len(target.snapshot.files)} files)")
        return True

    def unwatch(self, directory: str) -> bool:
        directory = os.path.abspath(directory)
        if directory in self._targets:
            del self._targets[directory]
            return True
        return False

    def on_change(self, callback: Callable) -> None:
        """Register a callback for file change events."""
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("File watcher started")

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("File watcher stopped")

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                all_events: List[FileEvent] = []

                for target in self._targets.values():
                    events = target.detect_changes()
                    for event in events:
                        # Debounce check
                        key = f"{event.path}:{event.event_type}"
                        now = time.time()
                        last = self._debounce_buffer.get(key, 0)
                        if now - last < self._debounce_ms / 1000:
                            continue
                        self._debounce_buffer[key] = now
                        all_events.append(event)

                # Process events
                for event in all_events:
                    event_dict = event.to_dict()
                    self._event_history.append(event_dict)

                    # Fire callbacks
                    for cb in self._callbacks:
                        try:
                            if asyncio.iscoroutinefunction(cb):
                                await cb(event)
                            else:
                                cb(event)
                        except Exception as e:
                            logger.warning(f"Watcher callback error: {e}")

                # Trim history
                if len(self._event_history) > self.MAX_EVENTS:
                    self._event_history = self._event_history[-self.MAX_EVENTS:]

                # Clean old debounce entries
                cutoff = time.time() - 10
                self._debounce_buffer = {
                    k: v for k, v in self._debounce_buffer.items() if v > cutoff
                }

            except Exception as e:
                logger.error(f"Watcher poll error: {e}")

            await asyncio.sleep(self._poll_interval)

    def get_watched(self) -> List[Dict[str, Any]]:
        """List all watched directories."""
        return [
            {
                "directory": target.directory,
                "label": target.label,
                "file_count": len(target.snapshot.files),
                "event_count": target.event_count,
                "last_event": target.last_event.to_dict() if target.last_event else None,
                "extensions": list(target.extensions) if target.extensions else None,
            }
            for target in self._targets.values()
        ]

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._event_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "watched_dirs": len(self._targets),
            "total_files": sum(len(t.snapshot.files) for t in self._targets.values()),
            "total_events": len(self._event_history),
            "running": self._running,
            "poll_interval": self._poll_interval,
        }

    @property
    def is_running(self) -> bool:
        return self._running


_watcher: Optional[FileWatcher] = None


def get_file_watcher() -> FileWatcher:
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher()
    return _watcher
