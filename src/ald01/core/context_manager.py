"""
ALD-01 Context Manager
Smart conversation context management with sliding window,
token counting, memory summarization, and context injection.
"""

import os
import json
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

from ald01 import DATA_DIR

logger = logging.getLogger("ald01.context")


class TokenEstimator:
    """
    Estimates token count without requiring tiktoken.
    Uses the ~4 chars/token heuristic for English text.
    """

    CHARS_PER_TOKEN = 4.0
    CODE_CHARS_PER_TOKEN = 3.5  # Code is denser

    @staticmethod
    def estimate(text: str) -> int:
        if not text:
            return 0
        # Simple heuristic: word count * 1.3 + special chars
        words = len(text.split())
        chars = len(text)
        estimated = max(words * 1.3, chars / TokenEstimator.CHARS_PER_TOKEN)
        return int(estimated)

    @staticmethod
    def estimate_messages(messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            total += TokenEstimator.estimate(msg.get("content", ""))
            total += 4  # Overhead per message (role, delimiters)
        total += 3  # Priming tokens
        return total


class ContextWindow:
    """
    Sliding window that keeps conversation within token limits.
    Preserves system messages and recent messages, summarizing middle.
    """

    def __init__(self, max_tokens: int = 8000, reserve_tokens: int = 2000):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens  # Reserve for response
        self.effective_limit = max_tokens - reserve_tokens

    def fit(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Trim messages to fit within the token limit."""
        if not messages:
            return []

        total = TokenEstimator.estimate_messages(messages)
        if total <= self.effective_limit:
            return messages

        # Separate system messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        system_tokens = TokenEstimator.estimate_messages(system_msgs)
        remaining = self.effective_limit - system_tokens

        # Keep most recent messages
        result = []
        cumulative = 0
        for msg in reversed(other_msgs):
            msg_tokens = TokenEstimator.estimate(msg.get("content", "")) + 4
            if cumulative + msg_tokens <= remaining:
                result.insert(0, msg)
                cumulative += msg_tokens
            else:
                break

        return system_msgs + result

    def get_utilization(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get token utilization stats."""
        total = TokenEstimator.estimate_messages(messages)
        return {
            "total_tokens": total,
            "max_tokens": self.max_tokens,
            "effective_limit": self.effective_limit,
            "utilization_pct": round(total / max(self.effective_limit, 1) * 100, 1),
            "remaining": max(0, self.effective_limit - total),
            "message_count": len(messages),
        }


class ConversationSummarizer:
    """
    Generates summaries of conversation segments for context compression.
    Uses extractive summarization (key sentences) since no LLM available locally.
    """

    MAX_SUMMARY_LENGTH = 500

    def summarize(self, messages: List[Dict[str, str]]) -> str:
        """Generate a brief summary of a conversation segment."""
        if not messages:
            return ""

        # Extract key points
        key_points = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "").strip()
            if not content:
                continue

            # Take first sentence of each message
            first_sentence = self._first_sentence(content)
            if len(first_sentence) > 10:
                key_points.append(f"[{role}] {first_sentence}")

        if not key_points:
            return "No significant content to summarize."

        summary = "Previous conversation summary:\n" + "\n".join(key_points[:10])
        if len(summary) > self.MAX_SUMMARY_LENGTH:
            summary = summary[:self.MAX_SUMMARY_LENGTH - 3] + "..."

        return summary

    @staticmethod
    def _first_sentence(text: str) -> str:
        for delim in [".", "!", "?", "\n"]:
            idx = text.find(delim)
            if 0 < idx < 200:
                return text[:idx + 1].strip()
        return text[:150].strip()


class ContextInjector:
    """
    Injects relevant context into conversations.
    Sources:
    - System prompt
    - Active project context
    - Recent tools/commands
    - User preferences
    - Time/date awareness
    """

    def __init__(self):
        self._pinned_context: List[Dict[str, str]] = []
        self._injections: Dict[str, str] = {}

    def set_injection(self, key: str, content: str) -> None:
        self._injections[key] = content

    def remove_injection(self, key: str) -> bool:
        if key in self._injections:
            del self._injections[key]
            return True
        return False

    def pin(self, message: Dict[str, str]) -> None:
        """Pin a message to always be included."""
        if len(self._pinned_context) < 5:
            self._pinned_context.append(message)

    def unpin(self, index: int) -> bool:
        if 0 <= index < len(self._pinned_context):
            self._pinned_context.pop(index)
            return True
        return False

    def get_context_block(self) -> str:
        """Generate the context injection block."""
        parts = []

        # Time awareness
        from datetime import datetime
        now = datetime.now()
        parts.append(f"Current date/time: {now.strftime('%Y-%m-%d %H:%M:%S %A')}")

        # Custom injections
        for key, content in self._injections.items():
            parts.append(f"[{key}]: {content}")

        if not parts:
            return ""

        return "\n\n---\nContext:\n" + "\n".join(parts) + "\n---"

    def get_augmented_messages(
        self, messages: List[Dict[str, str]], system_prompt: str = "",
    ) -> List[Dict[str, str]]:
        """Build the full message list with injections."""
        result = []

        # System prompt with context
        if system_prompt:
            context_block = self.get_context_block()
            full_system = system_prompt + context_block
            result.append({"role": "system", "content": full_system})

        # Pinned context
        for pinned in self._pinned_context:
            result.append(pinned)

        # Original messages (skip any existing system messages if we added one)
        for msg in messages:
            if msg.get("role") == "system" and system_prompt:
                continue
            result.append(msg)

        return result

    def list_injections(self) -> Dict[str, str]:
        return dict(self._injections)

    def list_pinned(self) -> List[Dict[str, str]]:
        return list(self._pinned_context)


class ContextMemory:
    """
    Long-term memory store for important facts across conversations.
    Stores key-value memories that persist across sessions.
    """

    MAX_MEMORIES = 200

    def __init__(self):
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._path = os.path.join(DATA_DIR, "context_memory.json")
        self._load()

    def remember(self, key: str, value: str, category: str = "general") -> None:
        """Store a memory."""
        self._memories[key] = {
            "value": value,
            "category": category,
            "created_at": time.time(),
            "access_count": 0,
            "last_accessed": time.time(),
        }
        # Enforce limit
        if len(self._memories) > self.MAX_MEMORIES:
            oldest = min(self._memories, key=lambda k: self._memories[k]["last_accessed"])
            del self._memories[oldest]
        self._save()

    def recall(self, key: str) -> Optional[str]:
        """Retrieve a memory by key."""
        mem = self._memories.get(key)
        if mem:
            mem["access_count"] += 1
            mem["last_accessed"] = time.time()
            return mem["value"]
        return None

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search memories by keyword."""
        query_lower = query.lower()
        results = []
        for key, mem in self._memories.items():
            if (query_lower in key.lower()
                    or query_lower in mem["value"].lower()
                    or query_lower in mem.get("category", "").lower()):
                results.append({
                    "key": key,
                    "value": mem["value"],
                    "category": mem["category"],
                    "access_count": mem["access_count"],
                })
        return results

    def forget(self, key: str) -> bool:
        if key in self._memories:
            del self._memories[key]
            self._save()
            return True
        return False

    def list_all(self, category: str = "") -> List[Dict[str, Any]]:
        memories = []
        for key, mem in self._memories.items():
            if category and mem.get("category") != category:
                continue
            memories.append({
                "key": key,
                "value": mem["value"][:100],
                "category": mem["category"],
                "access_count": mem["access_count"],
            })
        return sorted(memories, key=lambda m: m["access_count"], reverse=True)

    def get_categories(self) -> List[str]:
        cats = set()
        for mem in self._memories.values():
            cats.add(mem.get("category", "general"))
        return sorted(cats)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_memories": len(self._memories),
            "categories": self.get_categories(),
            "total_accesses": sum(m["access_count"] for m in self._memories.values()),
            "most_accessed": max(
                self._memories.items(),
                key=lambda x: x[1]["access_count"],
                default=("none", {"access_count": 0}),
            )[0],
        }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._memories, f, indent=2)
        except Exception as e:
            logger.warning(f"Context memory save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, encoding="utf-8") as f:
                    self._memories = json.load(f)
        except Exception:
            self._memories = {}


class ContextManager:
    """
    Orchestrates all context management subsystems.

    Components:
    - ContextWindow: Token-aware message trimming
    - ConversationSummarizer: Compresses old context
    - ContextInjector: Adds relevant context to messages
    - ContextMemory: Persistent fact storage
    """

    def __init__(self, max_tokens: int = 8000):
        self.window = ContextWindow(max_tokens)
        self.summarizer = ConversationSummarizer()
        self.injector = ContextInjector()
        self.memory = ContextMemory()

    def prepare_messages(
        self, messages: List[Dict[str, str]],
        system_prompt: str = "",
    ) -> List[Dict[str, str]]:
        """
        Full context preparation pipeline:
        1. Inject context (system prompt, time, pinned, custom)
        2. Fit to token window
        """
        augmented = self.injector.get_augmented_messages(messages, system_prompt)
        fitted = self.window.fit(augmented)
        return fitted

    def get_utilization(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return self.window.get_utilization(messages)

    def summarize_old_messages(
        self, messages: List[Dict[str, str]], keep_recent: int = 10,
    ) -> List[Dict[str, str]]:
        """Replace old messages with a summary."""
        if len(messages) <= keep_recent:
            return messages

        old = messages[:-keep_recent]
        recent = messages[-keep_recent:]

        summary = self.summarizer.summarize(old)
        summary_msg = {"role": "system", "content": summary}

        return [summary_msg] + recent

    def get_stats(self) -> Dict[str, Any]:
        return {
            "window": {
                "max_tokens": self.window.max_tokens,
                "effective_limit": self.window.effective_limit,
            },
            "injections": len(self.injector.list_injections()),
            "pinned_messages": len(self.injector.list_pinned()),
            "memory": self.memory.get_stats(),
        }


_context_mgr: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    global _context_mgr
    if _context_mgr is None:
        _context_mgr = ContextManager()
    return _context_mgr
