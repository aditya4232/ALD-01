"""
ALD-01 SubAgent Registry
Manages specialized AI sub-agents that can be deployed for specific tasks.
Each sub-agent has its own system prompt, tools, and capabilities.
"""

import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("ald01.subagents")


@dataclass
class SubAgent:
    """A specialized sub-agent."""
    id: str
    name: str
    display_name: str
    icon: str
    description: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    enabled: bool = True
    invocations: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_used: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "tools": self.tools,
            "capabilities": self.capabilities,
            "enabled": self.enabled,
            "invocations": self.invocations,
            "avg_latency_ms": round(self.avg_latency_ms),
            "success_rate": round(self.success_rate, 2),
            "last_used": self.last_used,
        }


BUILTIN_SUBAGENTS: Dict[str, SubAgent] = {
    "coder": SubAgent(
        id="coder", name="coder", display_name="🧑‍💻 Code Agent",
        icon="🧑‍💻", description="Writes, refactors, and optimizes code",
        system_prompt="You are a senior software engineer. Write clean, efficient, well-documented code.",
        tools=["file_read", "file_write", "terminal", "code_exec"],
        capabilities=["code_generation", "refactoring", "optimization", "debugging"],
    ),
    "debugger": SubAgent(
        id="debugger", name="debugger", display_name="🐛 Debug Agent",
        icon="🐛", description="Finds and fixes bugs, analyzes errors",
        system_prompt="You are a debugging specialist. Analyze errors, find root causes, suggest fixes.",
        tools=["file_read", "terminal", "code_exec", "browser"],
        capabilities=["error_analysis", "stack_trace", "logging", "breakpoint"],
    ),
    "reviewer": SubAgent(
        id="reviewer", name="reviewer", display_name="🔍 Review Agent",
        icon="🔍", description="Reviews code for quality, patterns, and best practices",
        system_prompt="You are a code reviewer. Check for bugs, security, performance, and style.",
        tools=["file_read"],
        capabilities=["code_review", "security_check", "perf_review", "style_check"],
    ),
    "security": SubAgent(
        id="security", name="security", display_name="🔒 Security Agent",
        icon="🔒", description="Security analysis, vulnerability scanning, threat modeling",
        system_prompt="You are a security expert. Analyze code for vulnerabilities and suggest mitigations.",
        tools=["file_read", "terminal", "browser"],
        capabilities=["vuln_scan", "threat_model", "secret_detection", "compliance"],
    ),
    "researcher": SubAgent(
        id="researcher", name="researcher", display_name="🔬 Research Agent",
        icon="🔬", description="Deep research, documentation, analysis",
        system_prompt="You are a research analyst. Gather information, analyze, and summarize findings.",
        tools=["browser", "clipboard"],
        capabilities=["web_research", "summarization", "analysis", "comparison"],
    ),
    "architect": SubAgent(
        id="architect", name="architect", display_name="🏗️ Architect Agent",
        icon="🏗️", description="System design, architecture review, planning",
        system_prompt="You are a software architect. Design scalable, maintainable systems.",
        tools=["file_read", "file_write"],
        capabilities=["system_design", "architecture", "planning", "diagramming"],
    ),
    "devops": SubAgent(
        id="devops", name="devops", display_name="⚙️ DevOps Agent",
        icon="⚙️", description="CI/CD, Docker, deployment, infrastructure",
        system_prompt="You are a DevOps engineer. Manage infrastructure, CI/CD, and deployment.",
        tools=["terminal", "file_read", "file_write"],
        capabilities=["docker", "cicd", "deployment", "monitoring"],
    ),
    "writer": SubAgent(
        id="writer", name="writer", display_name="✍️ Writer Agent",
        icon="✍️", description="Documentation, README, technical writing",
        system_prompt="You are a technical writer. Create clear, comprehensive documentation.",
        tools=["file_read", "file_write", "clipboard"],
        capabilities=["docs", "readme", "api_docs", "tutorials"],
    ),
    "general": SubAgent(
        id="general", name="general", display_name="🤖 General Agent",
        icon="🤖", description="General purpose AI assistant",
        system_prompt="You are a helpful AI assistant. Answer questions and help with tasks.",
        tools=["browser", "clipboard"],
        capabilities=["qa", "explanation", "planning", "brainstorming"],
    ),
    "doctor": SubAgent(
        id="doctor", name="doctor", display_name="🩺 Self-Heal Agent",
        icon="🩺", description="Diagnoses and repairs ALD-01 systems",
        system_prompt="You are ALD-01's internal doctor. Diagnose issues and apply fixes.",
        tools=["file_read", "file_write", "terminal"],
        capabilities=["diagnostics", "repair", "backup", "restore"],
    ),
}


class SubAgentRegistry:
    """
    Registry for managing sub-agents.
    Tracks usage, performance, and provides agent info for the dashboard.
    """

    def __init__(self):
        self._agents: Dict[str, SubAgent] = dict(BUILTIN_SUBAGENTS)

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values()]

    def get_active_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values() if a.enabled]

    def enable_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id].enabled = True
            return True
        return False

    def disable_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id].enabled = False
            return True
        return False

    def record_invocation(self, agent_id: str, latency_ms: float, success: bool) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.invocations += 1
            agent.last_used = time.time()
            n = agent.invocations
            agent.avg_latency_ms = (agent.avg_latency_ms * (n - 1) + latency_ms) / n
            agent.success_rate = (agent.success_rate * (n - 1) + (1.0 if success else 0.0)) / n

    def register_custom_agent(
        self,
        agent_id: str,
        name: str,
        display_name: str,
        icon: str,
        description: str,
        system_prompt: str,
        tools: List[str] = None,
        capabilities: List[str] = None,
    ) -> SubAgent:
        agent = SubAgent(
            id=agent_id, name=name, display_name=display_name,
            icon=icon, description=description, system_prompt=system_prompt,
            tools=tools or [], capabilities=capabilities or [],
        )
        self._agents[agent_id] = agent
        return agent

    def remove_custom_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents and agent_id not in BUILTIN_SUBAGENTS:
            del self._agents[agent_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_agents": len(self._agents),
            "enabled": sum(1 for a in self._agents.values() if a.enabled),
            "total_invocations": sum(a.invocations for a in self._agents.values()),
            "most_used": max(self._agents.values(), key=lambda a: a.invocations).name if self._agents else "",
        }


_registry: Optional[SubAgentRegistry] = None

def get_subagent_registry() -> SubAgentRegistry:
    global _registry
    if _registry is None:
        _registry = SubAgentRegistry()
    return _registry
