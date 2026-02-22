"""
ALD-01 Thinking Visualizer
Rich terminal UI for showing real-time AI thinking process.
Uses the Rich library for beautiful terminal output.
"""

import time
import asyncio
import logging
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich.layout import Layout
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ald01.core.events import get_event_bus, Event, EventType

logger = logging.getLogger("ald01.visualization")

console = Console()


class ThinkingVisualizer:
    """
    Real-time terminal visualization of ALD-01's thinking process.
    Shows:
    - Active reasoning steps
    - Agent selection
    - Provider routing
    - Tool execution
    - Response generation
    """

    def __init__(self):
        self._event_bus = get_event_bus()
        self._steps: List[Dict[str, Any]] = []
        self._current_agent = ""
        self._current_provider = ""
        self._status = "idle"
        self._registered = False

    async def start(self) -> None:
        """Register event handlers for visualization."""
        if self._registered:
            return

        self._event_bus.on(EventType.THINKING_STARTED, self._on_thinking_start)
        self._event_bus.on(EventType.THINKING_STEP, self._on_thinking_step)
        self._event_bus.on(EventType.THINKING_COMPLETED, self._on_thinking_complete)
        self._event_bus.on(EventType.AGENT_ROUTED, self._on_agent_routed)
        self._event_bus.on(EventType.AGENT_TASK_STARTED, self._on_agent_task_start)
        self._event_bus.on(EventType.AGENT_TASK_COMPLETED, self._on_agent_task_complete)
        self._event_bus.on(EventType.PROVIDER_REQUEST, self._on_provider_request)
        self._event_bus.on(EventType.PROVIDER_RESPONSE, self._on_provider_response)
        self._event_bus.on(EventType.TOOL_EXECUTED, self._on_tool_executed)

        self._registered = True
        logger.debug("Thinking visualizer started")

    async def stop(self) -> None:
        """Unregister event handlers."""
        self._registered = False

    def display_thinking_tree(self) -> None:
        """Display the current thinking process as a tree."""
        tree = Tree("[bold cyan]🧠 ALD-01 Thinking Process[/bold cyan]")

        for step in self._steps:
            step_type = step.get("type", "step")
            content = step.get("content", "")[:80]
            duration = step.get("duration_ms", 0)

            color_map = {
                "plan": "blue",
                "agent_selection": "magenta",
                "agent_routing": "magenta",
                "provider_request": "cyan",
                "provider_response": "cyan",
                "tool_execution": "green",
                "thinking": "yellow",
                "conclusion": "bold green",
            }
            color = color_map.get(step_type, "white")

            icon_map = {
                "plan": "📋",
                "agent_selection": "🤖",
                "agent_routing": "🔀",
                "provider_request": "📡",
                "provider_response": "📨",
                "tool_execution": "🔧",
                "thinking": "💭",
                "conclusion": "✅",
            }
            icon = icon_map.get(step_type, "•")

            duration_str = f" ({duration:.0f}ms)" if duration > 0 else ""
            tree.add(f"[{color}]{icon} {step_type}: {content}{duration_str}[/{color}]")

        console.print(tree)

    def display_status_panel(self) -> None:
        """Display a compact status panel."""
        panels = []

        # Agent info
        if self._current_agent:
            panels.append(f"[magenta]🤖 Agent:[/magenta] {self._current_agent}")
        if self._current_provider:
            panels.append(f"[cyan]📡 Provider:[/cyan] {self._current_provider}")

        status_color = {"idle": "dim", "thinking": "yellow", "processing": "cyan", "done": "green"}
        color = status_color.get(self._status, "white")
        panels.append(f"[{color}]Status: {self._status}[/{color}]")

        if panels:
            console.print(Panel(
                "\n".join(panels),
                title="[bold]ALD-01 Status[/bold]",
                border_style="dim",
            ))

    # ──────────────────────────────────────────────────────────
    # Event Handlers
    # ──────────────────────────────────────────────────────────

    async def _on_thinking_start(self, event: Event) -> None:
        self._status = "thinking"
        self._steps = []
        strategy = event.data.get("strategy", "")
        depth = event.data.get("depth", 0)
        self._steps.append({
            "type": "plan",
            "content": f"Strategy: {strategy} (depth: {depth})",
            "timestamp": time.time(),
        })
        console.print(f"  [dim]💭 Reasoning with {strategy} strategy...[/dim]")

    async def _on_thinking_step(self, event: Event) -> None:
        step_type = event.data.get("step", "thinking")
        content = str(event.data)[:100]
        self._steps.append({
            "type": step_type,
            "content": content,
            "timestamp": time.time(),
        })
        console.print(f"  [dim]  → {step_type}: {content[:60]}[/dim]")

    async def _on_thinking_complete(self, event: Event) -> None:
        self._status = "done"
        self._steps.append({
            "type": "conclusion",
            "content": "Reasoning complete",
            "timestamp": time.time(),
        })

    async def _on_agent_routed(self, event: Event) -> None:
        agent = event.data.get("agent", "")
        self._current_agent = agent
        auto = event.data.get("auto_selected", True)
        mode = "auto-selected" if auto else "manual"
        self._steps.append({
            "type": "agent_routing",
            "content": f"Routed to {agent} ({mode})",
            "timestamp": time.time(),
        })
        console.print(f"  [dim]🤖 Agent: {agent} ({mode})[/dim]")

    async def _on_agent_task_start(self, event: Event) -> None:
        self._status = "processing"
        agent = event.data.get("agent", "")
        self._steps.append({
            "type": "agent_start",
            "content": f"{agent} processing...",
            "timestamp": time.time(),
        })

    async def _on_agent_task_complete(self, event: Event) -> None:
        latency = event.data.get("latency_ms", 0)
        model = event.data.get("model", "")
        self._status = "done"
        self._steps.append({
            "type": "conclusion",
            "content": f"Done via {model}",
            "duration_ms": latency,
            "timestamp": time.time(),
        })

    async def _on_provider_request(self, event: Event) -> None:
        provider = event.data.get("provider", "")
        model = event.data.get("model", "")
        self._current_provider = f"{provider} ({model})"
        self._steps.append({
            "type": "provider_request",
            "content": f"Sending to {provider} ({model})",
            "timestamp": time.time(),
        })
        console.print(f"  [dim]📡 Provider: {provider} → {model}[/dim]")

    async def _on_provider_response(self, event: Event) -> None:
        latency = event.data.get("latency_ms", 0)
        self._steps.append({
            "type": "provider_response",
            "content": f"Response received",
            "duration_ms": latency,
            "timestamp": time.time(),
        })

    async def _on_tool_executed(self, event: Event) -> None:
        tool = event.data.get("tool", "")
        self._steps.append({
            "type": "tool_execution",
            "content": f"Executed: {tool}",
            "timestamp": time.time(),
        })
        console.print(f"  [dim]🔧 Tool: {tool}[/dim]")

    def get_steps(self) -> List[Dict[str, Any]]:
        """Get current thinking steps."""
        return self._steps.copy()

    def clear(self) -> None:
        """Clear thinking steps."""
        self._steps.clear()
        self._status = "idle"


# Singleton
_visualizer: Optional[ThinkingVisualizer] = None


def get_visualizer() -> ThinkingVisualizer:
    """Get or create the global thinking visualizer."""
    global _visualizer
    if _visualizer is None:
        _visualizer = ThinkingVisualizer()
    return _visualizer
