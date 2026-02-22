"""
ALD-01 Memory Manager
SQLite-backed persistent memory with conversation history, semantic search, and context management.
"""

import os
import json
import time
import hashlib
import logging
import sqlite3
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from ald01 import MEMORY_DIR
from ald01.config import get_config

logger = logging.getLogger("ald01.memory")


@dataclass
class Message:
    """A single conversation message."""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    agent: str = "general"
    timestamp: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
        }

    def to_api_format(self) -> Dict[str, str]:
        """Convert to OpenAI-compatible message format."""
        return {"role": self.role, "content": self.content}


@dataclass
class Conversation:
    """A conversation session."""
    id: str
    title: str = "New Conversation"
    created_at: float = 0.0
    updated_at: float = 0.0
    agent: str = "general"
    messages: List[Message] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.updated_at == 0.0:
            self.updated_at = time.time()
        if self.messages is None:
            self.messages = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MemoryEntry:
    """A semantic memory entry (learned fact, pattern, preference)."""
    id: str
    category: str  # 'fact', 'preference', 'pattern', 'skill', 'identity'
    content: str
    importance: float = 0.5  # 0.0 to 1.0
    created_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0
    tags: List[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.accessed_at == 0.0:
            self.accessed_at = time.time()
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class MemoryManager:
    """Manages persistent memory storage using SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        config = get_config()
        self.db_path = db_path or config.get("memory", "db_path", default=os.path.join(MEMORY_DIR, "ald01.db"))
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._current_conversation_id: Optional[str] = None
        self._setup_database()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _setup_database(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Conversation',
                agent TEXT NOT NULL DEFAULT 'general',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                agent TEXT DEFAULT 'general',
                timestamp REAL NOT NULL,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                accessed_at REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decision_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                decision_type TEXT NOT NULL,
                agent TEXT,
                input_summary TEXT,
                decision TEXT NOT NULL,
                reasoning TEXT,
                outcome TEXT,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS thinking_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                conversation_id TEXT,
                thought_type TEXT NOT NULL,
                content TEXT NOT NULL,
                depth INTEGER DEFAULT 0,
                duration_ms REAL DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);
            CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_memories_imp ON memories(importance DESC);
            CREATE INDEX IF NOT EXISTS idx_decision_ts ON decision_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_thinking_conv ON thinking_log(conversation_id);
        """)
        conn.commit()

    # ──────────────────────────────────────────────────────────
    # Conversation Management
    # ──────────────────────────────────────────────────────────

    def create_conversation(self, title: str = "New Conversation", agent: str = "general") -> str:
        """Create a new conversation and return its ID."""
        conv_id = hashlib.md5(f"{time.time()}_{title}".encode()).hexdigest()[:12]
        now = time.time()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO conversations (id, title, agent, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, title, agent, now, now),
        )
        conn.commit()
        self._current_conversation_id = conv_id
        logger.info(f"Created conversation: {conv_id} - {title}")
        return conv_id

    def get_or_create_conversation(self, conv_id: Optional[str] = None) -> str:
        """Get existing conversation or create a new one."""
        if conv_id:
            conn = self._get_conn()
            row = conn.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if row:
                self._current_conversation_id = conv_id
                return conv_id

        if self._current_conversation_id:
            return self._current_conversation_id

        return self.create_conversation()

    def list_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent conversations."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation and its messages."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
        if self._current_conversation_id == conv_id:
            self._current_conversation_id = None
        return True

    # ──────────────────────────────────────────────────────────
    # Message Management
    # ──────────────────────────────────────────────────────────

    def add_message(self, message: Message, conv_id: Optional[str] = None) -> None:
        """Add a message to a conversation."""
        cid = conv_id or self.get_or_create_conversation()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, agent, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (cid, message.role, message.content, message.agent, message.timestamp, json.dumps(message.metadata or {})),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ?, title = CASE WHEN title = 'New Conversation' THEN ? ELSE title END WHERE id = ?",
            (time.time(), message.content[:60] if message.role == "user" else "New Conversation", cid),
        )
        conn.commit()

    def get_messages(self, conv_id: Optional[str] = None, limit: int = 50) -> List[Message]:
        """Get messages for a conversation."""
        cid = conv_id or self._current_conversation_id
        if not cid:
            return []
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT role, content, agent, timestamp, metadata FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC LIMIT ?",
            (cid, limit),
        ).fetchall()
        messages = []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r["metadata"]) if r["metadata"] else {}
            except (json.JSONDecodeError, TypeError):
                pass
            messages.append(Message(
                role=r["role"],
                content=r["content"],
                agent=r["agent"],
                timestamp=r["timestamp"],
                metadata=meta,
            ))
        return messages

    def get_context_messages(self, conv_id: Optional[str] = None, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get messages formatted for API context (OpenAI format)."""
        messages = self.get_messages(conv_id, limit=max_messages)
        return [m.to_api_format() for m in messages]

    def clear_messages(self, conv_id: Optional[str] = None) -> None:
        """Clear all messages in a conversation."""
        cid = conv_id or self._current_conversation_id
        if cid:
            conn = self._get_conn()
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
            conn.commit()

    # ──────────────────────────────────────────────────────────
    # Semantic Memory (Long-term Knowledge)
    # ──────────────────────────────────────────────────────────

    def store_memory(self, category: str, content: str, importance: float = 0.5,
                     tags: Optional[List[str]] = None, metadata: Optional[Dict] = None) -> str:
        """Store a semantic memory entry."""
        mem_id = hashlib.md5(f"{category}_{content[:100]}_{time.time()}".encode()).hexdigest()[:12]
        now = time.time()
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO memories (id, category, content, importance, created_at, accessed_at, access_count, tags, metadata) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (mem_id, category, content, importance, now, now, json.dumps(tags or []), json.dumps(metadata or {})),
        )
        conn.commit()
        logger.debug(f"Stored memory: {mem_id} [{category}] - {content[:50]}...")
        return mem_id

    def search_memories(self, query: str, category: Optional[str] = None,
                        limit: int = 10) -> List[MemoryEntry]:
        """Search memories by keyword (simple text matching)."""
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category = ? AND content LIKE ? ORDER BY importance DESC, accessed_at DESC LIMIT ?",
                (category, f"%{query}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY importance DESC, accessed_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()

        entries = []
        for r in rows:
            tags = []
            try:
                tags = json.loads(r["tags"]) if r["tags"] else []
            except (json.JSONDecodeError, TypeError):
                pass
            meta = {}
            try:
                meta = json.loads(r["metadata"]) if r["metadata"] else {}
            except (json.JSONDecodeError, TypeError):
                pass

            entry = MemoryEntry(
                id=r["id"],
                category=r["category"],
                content=r["content"],
                importance=r["importance"],
                created_at=r["created_at"],
                accessed_at=r["accessed_at"],
                access_count=r["access_count"],
                tags=tags,
                metadata=meta,
            )
            entries.append(entry)

            # Update access
            conn.execute(
                "UPDATE memories SET accessed_at = ?, access_count = access_count + 1 WHERE id = ?",
                (time.time(), r["id"]),
            )
        conn.commit()
        return entries

    def get_memories_by_category(self, category: str, limit: int = 20) -> List[MemoryEntry]:
        """Get all memories in a category."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM memories WHERE category = ? ORDER BY importance DESC LIMIT ?",
            (category, limit),
        ).fetchall()
        return [MemoryEntry(
            id=r["id"], category=r["category"], content=r["content"],
            importance=r["importance"], created_at=r["created_at"],
            accessed_at=r["accessed_at"], access_count=r["access_count"],
        ) for r in rows]

    def delete_memory(self, mem_id: str) -> bool:
        """Delete a specific memory entry."""
        conn = self._get_conn()
        conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        conn.commit()
        return True

    # ──────────────────────────────────────────────────────────
    # User Profile
    # ──────────────────────────────────────────────────────────

    def set_user_profile(self, key: str, value: str) -> None:
        """Set a user profile value."""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        conn.commit()

    def get_user_profile(self, key: str, default: str = "") -> str:
        """Get a user profile value."""
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM user_profile WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def get_all_user_profile(self) -> Dict[str, str]:
        """Get all user profile entries."""
        conn = self._get_conn()
        rows = conn.execute("SELECT key, value FROM user_profile").fetchall()
        return {r["key"]: r["value"] for r in rows}

    # ──────────────────────────────────────────────────────────
    # Decision Log
    # ──────────────────────────────────────────────────────────

    def log_decision(self, decision_type: str, decision: str, agent: str = "",
                     input_summary: str = "", reasoning: str = "", outcome: str = "") -> None:
        """Log an AI decision for transparency."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO decision_log (timestamp, decision_type, agent, input_summary, decision, reasoning, outcome) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), decision_type, agent, input_summary, decision, reasoning, outcome),
        )
        conn.commit()

    def get_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent decisions."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM decision_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────
    # Thinking Log
    # ──────────────────────────────────────────────────────────

    def log_thinking(self, thought_type: str, content: str, depth: int = 0,
                     duration_ms: float = 0, conv_id: Optional[str] = None) -> None:
        """Log a thinking step."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO thinking_log (timestamp, conversation_id, thought_type, content, depth, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), conv_id or self._current_conversation_id, thought_type, content, depth, duration_ms),
        )
        conn.commit()

    def get_thinking_log(self, conv_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get thinking log entries."""
        conn = self._get_conn()
        cid = conv_id or self._current_conversation_id
        if cid:
            rows = conn.execute(
                "SELECT * FROM thinking_log WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
                (cid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM thinking_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        conn = self._get_conn()
        conv_count = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
        msg_count = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
        mem_count = conn.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
        dec_count = conn.execute("SELECT COUNT(*) as c FROM decision_log").fetchone()["c"]
        think_count = conn.execute("SELECT COUNT(*) as c FROM thinking_log").fetchone()["c"]

        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        return {
            "conversations": conv_count,
            "messages": msg_count,
            "memories": mem_count,
            "decisions": dec_count,
            "thinking_steps": think_count,
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "db_path": self.db_path,
        }

    def cleanup(self, days: int = 90) -> int:
        """Remove old conversations and messages."""
        cutoff = time.time() - (days * 86400)
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE updated_at < ?)",
            (cutoff,),
        )
        deleted = cursor.rowcount
        conn.execute("DELETE FROM conversations WHERE updated_at < ?", (cutoff,))
        conn.commit()
        logger.info(f"Cleaned up {deleted} old messages (older than {days} days)")
        return deleted

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Singleton
_memory_instance: Optional[MemoryManager] = None


def get_memory() -> MemoryManager:
    """Get or create the global memory manager instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryManager()
    return _memory_instance
