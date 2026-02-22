"""
ALD-01 Orchestrator
Central coordinator that routes requests to agents, manages providers, and orchestrates the system.
"""

import time
import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from ald01.config import get_config, get_brain_power_preset
from ald01.core.memory import get_memory, Message
from ald01.core.events import get_event_bus, Event, EventType
from ald01.core.tools import get_tool_executor
from ald01.providers.manager import get_provider_manager
from ald01.providers.base import CompletionRequest
from ald01.agents.base import BaseAgent, AgentTask, AgentResponse
from ald01.agents.codegen import CodeGenAgent
from ald01.agents.debug import DebugAgent
from ald01.agents.review import ReviewAgent
from ald01.agents.security import SecurityAgent
from ald01.agents.general import GeneralAgent

logger = logging.getLogger("ald01.orchestrator")


class Orchestrator:
    """
    Central coordinator for ALD-01.
    - Routes queries to the best agent
    - Manages conversation state
    - Provides streaming and non-streaming responses
    - Tracks all activity for the visualizer
    """

    def __init__(self):
        self._config = get_config()
        self._memory = get_memory()
        self._event_bus = get_event_bus()
        self._provider_manager = get_provider_manager()
        self._tool_executor = get_tool_executor()
        self._agents: Dict[str, BaseAgent] = {}
        self._initialized = False
        self._start_time = time.time()
        self._total_requests = 0
        self._activity_log: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize the orchestrator and all subsystems."""
        if self._initialized:
            return

        logger.info("Initializing ALD-01 Orchestrator...")

        await self._event_bus.emit(Event(
            type=EventType.SYSTEM_STARTING,
            data={"version": "1.0.0"},
        ))

        # Initialize providers
        await self._provider_manager.initialize()

        # Register agents
        self._agents = {
            "code_gen": CodeGenAgent(),
            "debug": DebugAgent(),
            "review": ReviewAgent(),
            "security": SecurityAgent(),
            "general": GeneralAgent(),
        }

        self._initialized = True
        self._start_time = time.time()

        await self._event_bus.emit(Event(
            type=EventType.SYSTEM_STARTED,
            data={
                "agents": list(self._agents.keys()),
                "providers": self._provider_manager.list_providers(),
            },
        ))

        logger.info(
            f"ALD-01 Orchestrator ready — "
            f"{len(self._agents)} agents, "
            f"{len(self._provider_manager.list_providers())} providers"
        )

    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator."""
        await self._event_bus.emit(Event(
            type=EventType.SYSTEM_STOPPING,
            data={"uptime_seconds": time.time() - self._start_time},
        ))
        self._memory.close()
        self._initialized = False
        await self._event_bus.emit(Event(type=EventType.SYSTEM_STOPPED))
        logger.info("ALD-01 Orchestrator stopped.")

    # ──────────────────────────────────────────────────────────
    # Query Processing
    # ──────────────────────────────────────────────────────────

    async def process_query(
        self,
        query: str,
        agent_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process a user query:
        1. Select the best agent (or use specified)
        2. Build context from memory
        3. Send to provider
        4. Store response in memory
        5. Return result
        """
        if not self._initialized:
            await self.initialize()

        self._total_requests += 1
        start_time = time.time()

        # Get or create conversation
        conv_id = self._memory.get_or_create_conversation(conversation_id)

        # Log activity
        activity = {
            "type": "query",
            "timestamp": time.time(),
            "query": query[:100],
            "status": "processing",
        }
        self._activity_log.append(activity)

        # Select agent
        selected_agent = await self._select_agent(query, agent_name)

        await self._event_bus.emit(Event(
            type=EventType.AGENT_ROUTED,
            data={
                "agent": selected_agent.name,
                "query": query[:100],
                "auto_selected": agent_name is None,
            },
            source="orchestrator",
        ))

        # Process with agent
        task = AgentTask(
            query=query,
            agent_name=selected_agent.name,
            conversation_id=conv_id,
        )

        response = await selected_agent.process(task)
        response.metadata["conversation_id"] = conv_id

        # Update activity
        activity["status"] = "completed"
        activity["agent"] = selected_agent.name
        activity["latency_ms"] = response.latency_ms

        # Keep activity log bounded
        if len(self._activity_log) > 200:
            self._activity_log = self._activity_log[-200:]

        return response

    async def stream_query(
        self,
        query: str,
        agent_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream a response chunk by chunk."""
        if not self._initialized:
            await self.initialize()

        self._total_requests += 1
        conv_id = self._memory.get_or_create_conversation(conversation_id)
        selected_agent = await self._select_agent(query, agent_name)

        # Store user message
        self._memory.add_message(
            Message(role="user", content=query, agent=selected_agent.name),
            conv_id=conv_id,
        )

        # Get context
        context_messages = self._memory.get_context_messages(conv_id, max_messages=20)
        messages = context_messages + [{"role": "user", "content": query}]

        # Build request
        brain = get_brain_power_preset(self._config.brain_power)
        request = CompletionRequest(
            messages=messages,
            model=selected_agent.agent_config.get("model", "auto"),
            temperature=selected_agent.agent_config.get("temperature", 0.7),
            max_tokens=min(
                selected_agent.agent_config.get("max_tokens", 4096),
                brain["context_window"],
            ),
            system_prompt=selected_agent.system_prompt,
            stream=True,
        )

        # Stream from provider
        full_response = ""
        async for chunk in self._provider_manager.stream(request):
            full_response += chunk
            yield chunk

        # Store assistant response
        self._memory.add_message(
            Message(role="assistant", content=full_response, agent=selected_agent.name),
            conv_id=conv_id,
        )

    # ──────────────────────────────────────────────────────────
    # Agent Selection
    # ──────────────────────────────────────────────────────────

    async def _select_agent(self, query: str, preferred: Optional[str] = None) -> BaseAgent:
        """Select the best agent for a query."""
        # If explicitly specified
        if preferred and preferred in self._agents:
            agent = self._agents[preferred]
            if agent.enabled:
                return agent

        # Auto-select based on match scoring
        best_agent = None
        best_score = -1.0

        for name, agent in self._agents.items():
            if not agent.enabled:
                continue
            score = agent.matches(query)
            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent is None:
            best_agent = self._agents.get("general", GeneralAgent())

        # Log the decision
        self._memory.log_decision(
            decision_type="agent_selection",
            decision=f"Selected {best_agent.name} (score: {best_score:.2f})",
            agent=best_agent.name,
            input_summary=query[:100],
            reasoning=f"Auto-routing based on keyword matching",
        )

        await self._event_bus.emit(Event(
            type=EventType.THINKING_STEP,
            data={
                "step": "agent_selection",
                "selected": best_agent.name,
                "score": best_score,
                "query_preview": query[:60],
            },
            source="orchestrator",
        ))

        return best_agent

    # ──────────────────────────────────────────────────────────
    # Tool Execution
    # ──────────────────────────────────────────────────────────

    async def execute_tool(self, tool_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        result = await self._tool_executor.execute(tool_name, params)
        return result.to_dict()

    # ──────────────────────────────────────────────────────────
    # System Status & Stats
    # ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        uptime = time.time() - self._start_time
        return {
            "status": "running" if self._initialized else "stopped",
            "version": "1.0.0",
            "uptime_seconds": round(uptime),
            "uptime_human": self._format_uptime(uptime),
            "brain_power": self._config.brain_power,
            "brain_power_name": get_brain_power_preset(self._config.brain_power)["name"],
            "total_requests": self._total_requests,
            "agents": {name: agent.get_stats() for name, agent in self._agents.items()},
            "providers": self._provider_manager.get_stats(),
            "memory": self._memory.get_stats(),
            "tools": self._tool_executor.get_stats(),
        }

    def get_activity_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity for the visualizer."""
        return self._activity_log[-limit:]

    def get_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all agent info."""
        return {name: agent.get_stats() for name, agent in self._agents.items()}

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable form."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"


# Singleton
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
