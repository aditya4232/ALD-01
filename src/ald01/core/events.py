"""
ALD-01 Event System
Lightweight pub-sub event bus for decoupled component communication.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("ald01.events")


class EventType(str, Enum):
    """System event types."""
    # System lifecycle
    SYSTEM_STARTING = "system.starting"
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPING = "system.stopping"
    SYSTEM_STOPPED = "system.stopped"
    SYSTEM_ERROR = "system.error"

    # Agent events
    AGENT_TASK_RECEIVED = "agent.task.received"
    AGENT_TASK_STARTED = "agent.task.started"
    AGENT_TASK_COMPLETED = "agent.task.completed"
    AGENT_TASK_FAILED = "agent.task.failed"
    AGENT_ROUTED = "agent.routed"

    # Provider events
    PROVIDER_CONNECTED = "provider.connected"
    PROVIDER_DISCONNECTED = "provider.disconnected"
    PROVIDER_ERROR = "provider.error"
    PROVIDER_REQUEST = "provider.request"
    PROVIDER_RESPONSE = "provider.response"

    # Reasoning events
    THINKING_STARTED = "thinking.started"
    THINKING_STEP = "thinking.step"
    THINKING_COMPLETED = "thinking.completed"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_CLEARED = "memory.cleared"

    # Dashboard events
    DASHBOARD_UPDATE = "dashboard.update"
    DASHBOARD_CONNECTED = "dashboard.connected"

    # Tool events
    TOOL_EXECUTED = "tool.executed"
    TOOL_ERROR = "tool.error"

    # Chat events
    CHAT_MESSAGE = "chat.message"
    CHAT_RESPONSE = "chat.response"
    CHAT_STREAM_CHUNK = "chat.stream.chunk"
    CHAT_STREAM_END = "chat.stream.end"

    # User events
    USER_INPUT = "user.input"
    USER_COMMAND = "user.command"

    # Doctor events
    DOCTOR_CHECK = "doctor.check"
    DOCTOR_RESULT = "doctor.result"
    DOCTOR_FIX = "doctor.fix"


@dataclass
class Event:
    """Represents a system event."""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"{self.type.value}_{int(self.timestamp * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
        }


class EventBus:
    """Asynchronous event bus for component communication."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._sync_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history = 1000
        self._subscribers: Set[asyncio.Queue] = set()

    def on(self, event_type: EventType, handler: Callable) -> None:
        """Register an async event handler."""
        self._handlers[event_type.value].append(handler)

    def on_sync(self, event_type: EventType, handler: Callable) -> None:
        """Register a synchronous event handler."""
        self._sync_handlers[event_type.value].append(handler)

    def off(self, event_type: EventType, handler: Callable) -> None:
        """Remove an event handler."""
        key = event_type.value
        if key in self._handlers:
            self._handlers[key] = [h for h in self._handlers[key] if h != handler]
        if key in self._sync_handlers:
            self._sync_handlers[key] = [h for h in self._sync_handlers[key] if h != handler]

    async def emit(self, event: Event) -> None:
        """Emit an event to all handlers."""
        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        event_key = event.type.value

        # Notify async handlers
        for handler in self._handlers.get(event_key, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in async handler for {event_key}: {e}")

        # Notify sync handlers
        for handler in self._sync_handlers.get(event_key, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in sync handler for {event_key}: {e}")

        # Notify wildcard handlers
        for handler in self._handlers.get("*", []):
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in wildcard handler: {e}")

        # Push to subscribers (WebSocket, etc.)
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def emit_sync(self, event: Event) -> None:
        """Emit event synchronously (for non-async contexts)."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        event_key = event.type.value
        for handler in self._sync_handlers.get(event_key, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in sync handler for {event_key}: {e}")

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to all events via an async queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        self._subscribers.discard(queue)

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 50) -> List[Event]:
        """Get recent event history, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Global event bus singleton
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
