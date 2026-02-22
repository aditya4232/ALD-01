"""
ALD-01 Base Agent
Abstract base class for all specialized AI agents.
Handles prompt construction, tool invocation, and response processing.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ald01.config import get_config, get_brain_power_preset
from ald01.providers.base import CompletionRequest, CompletionResponse
from ald01.providers.manager import get_provider_manager
from ald01.core.memory import get_memory, Message
from ald01.core.events import get_event_bus, Event, EventType

logger = logging.getLogger("ald01.agents")


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    query: str
    agent_name: str = "general"
    conversation_id: Optional[str] = None
    context: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class AgentResponse:
    """Response from an agent."""
    content: str
    agent_name: str = ""
    model: str = ""
    provider: str = ""
    thinking: List[str] = field(default_factory=list)
    tools_used: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "agent": self.agent_name,
            "model": self.model,
            "provider": self.provider,
            "thinking": self.thinking,
            "tools_used": self.tools_used,
            "latency_ms": round(self.latency_ms, 1),
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    """
    Base class for AI agents. Each agent has:
    - A unique name and expertise area
    - A system prompt defining its personality
    - Access to tools and memory
    - Configurable model, temperature, etc.
    """

    def __init__(self, name: str, display_name: str, expertise: str):
        self.name = name
        self.display_name = display_name
        self.expertise = expertise
        self._config = get_config()
        self._memory = get_memory()
        self._event_bus = get_event_bus()
        self._task_count = 0
        self._total_latency = 0.0
        self._status = "idle"  # idle, processing, error

    @property
    def agent_config(self) -> Dict[str, Any]:
        """Get this agent's configuration."""
        return self._config.get_agent_config(self.name) or {}

    @property
    def enabled(self) -> bool:
        return self.agent_config.get("enabled", True)

    @property
    def system_prompt(self) -> str:
        """Build the full system prompt for this agent."""
        base_prompt = self.agent_config.get("system_prompt", self._default_system_prompt())
        brain = get_brain_power_preset(self._config.brain_power)

        # Enhance system prompt based on brain power
        enhancements = []
        if brain["reasoning_depth"] >= 3:
            enhancements.append("Think step by step before answering.")
        if brain["reasoning_depth"] >= 5:
            enhancements.append("Consider multiple approaches and choose the best one.")
        if brain["reasoning_depth"] >= 7:
            enhancements.append("Provide comprehensive analysis with pros, cons, and trade-offs.")
        if brain["autonomous"]:
            enhancements.append("You may suggest proactive actions when appropriate.")

        detail_map = {
            "brief": "Keep responses concise.",
            "standard": "Provide clear, well-structured responses.",
            "detailed": "Provide detailed, thorough responses with examples.",
            "exhaustive": "Provide exhaustive, comprehensive responses covering all aspects.",
        }
        enhancements.append(detail_map.get(brain["response_detail"], ""))

        if enhancements:
            base_prompt += "\n\n" + "\n".join(e for e in enhancements if e)

        return base_prompt

    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Return the default system prompt for this agent type."""
        ...

    @abstractmethod
    def matches(self, query: str) -> float:
        """Return a 0.0-1.0 score of how well this agent matches the query."""
        ...

    async def process(self, task: AgentTask) -> AgentResponse:
        """Process a task and return a response."""
        self._status = "processing"
        start_time = time.time()

        await self._event_bus.emit(Event(
            type=EventType.AGENT_TASK_STARTED,
            data={"agent": self.name, "query": task.query[:100]},
            source=f"agent.{self.name}",
        ))

        try:
            # Get conversation context
            context_messages = []
            if task.conversation_id:
                context_messages = self._memory.get_context_messages(
                    task.conversation_id,
                    max_messages=self.agent_config.get("max_context", 20),
                )

            # Add the current query
            messages = context_messages + [{"role": "user", "content": task.query}]

            # Build completion request
            brain = get_brain_power_preset(self._config.brain_power)
            request = CompletionRequest(
                messages=messages,
                model=self.agent_config.get("model", "auto"),
                temperature=self.agent_config.get("temperature", 0.7),
                max_tokens=min(
                    self.agent_config.get("max_tokens", 4096),
                    brain["context_window"],
                ),
                system_prompt=self.system_prompt,
            )

            # Send to provider
            provider_manager = get_provider_manager()
            completion = await provider_manager.complete(request)

            latency = (time.time() - start_time) * 1000

            # Store messages in memory
            self._memory.add_message(
                Message(role="user", content=task.query, agent=self.name),
                conv_id=task.conversation_id,
            )
            self._memory.add_message(
                Message(role="assistant", content=completion.content, agent=self.name),
                conv_id=task.conversation_id,
            )

            # Log decision
            self._memory.log_decision(
                decision_type="agent_response",
                decision=f"Routed to {self.name}, responded with {len(completion.content)} chars",
                agent=self.name,
                input_summary=task.query[:100],
                reasoning=f"Model: {completion.model}, Provider: {completion.provider}",
            )

            self._task_count += 1
            self._total_latency += latency
            self._status = "idle"

            response = AgentResponse(
                content=completion.content,
                agent_name=self.name,
                model=completion.model,
                provider=completion.provider,
                latency_ms=latency,
            )

            await self._event_bus.emit(Event(
                type=EventType.AGENT_TASK_COMPLETED,
                data={
                    "agent": self.name,
                    "model": completion.model,
                    "latency_ms": latency,
                    "content_length": len(completion.content),
                },
                source=f"agent.{self.name}",
            ))

            return response

        except Exception as e:
            self._status = "error"
            await self._event_bus.emit(Event(
                type=EventType.AGENT_TASK_FAILED,
                data={"agent": self.name, "error": str(e)},
                source=f"agent.{self.name}",
            ))
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        avg_latency = (self._total_latency / self._task_count) if self._task_count > 0 else 0
        return {
            "name": self.name,
            "display_name": self.display_name,
            "expertise": self.expertise,
            "enabled": self.enabled,
            "status": self._status,
            "tasks_completed": self._task_count,
            "avg_latency_ms": round(avg_latency, 1),
            "model": self.agent_config.get("model", "auto"),
        }
