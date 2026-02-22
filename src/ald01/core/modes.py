"""
ALD-01 Modes System
User-switchable operational modes that change ALD-01's focus and behavior.
Modes: code, research, review, security, custom, default
Each mode adjusts system prompts, agent priority, reasoning strategy, and tool access.
"""

import os
import time
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.modes")


class ModeType(str, Enum):
    """Available operational modes."""
    DEFAULT = "default"
    CODE = "code"
    RESEARCH = "research"
    REVIEW = "review"
    SECURITY = "security"
    CUSTOM = "custom"
    LEARNING = "learning"
    CREATIVE = "creative"
    DEBUG = "debug"
    DEVOPS = "devops"


@dataclass
class ModeProfile:
    """Complete profile for an operational mode."""
    mode_type: ModeType
    display_name: str
    icon: str
    description: str
    color: str  # Rich color name
    primary_agent: str  # Which agent to prefer
    agent_weights: Dict[str, float]  # Agent routing weight overrides
    system_prompt_addon: str  # Extra instructions appended to system prompt
    reasoning_strategy: str  # Preferred reasoning approach
    reasoning_depth_modifier: int  # How much to add/subtract from brain power depth
    creativity_modifier: float  # Adjust creativity (-0.5 to +0.5)
    tool_overrides: Dict[str, bool]  # Force enable/disable specific tools
    custom_instructions: str  # User-defined custom instructions
    focus_keywords: List[str]  # Keywords that activate this mode
    max_response_length: int  # Preferred response detail level
    enable_voice: Optional[bool]  # Override voice setting (None = use global)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode_type.value,
            "display_name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "color": self.color,
            "primary_agent": self.primary_agent,
            "reasoning_strategy": self.reasoning_strategy,
            "reasoning_depth_modifier": self.reasoning_depth_modifier,
            "creativity_modifier": self.creativity_modifier,
            "custom_instructions": self.custom_instructions,
            "metadata": self.metadata,
        }


# ──────────────────────────────────────────────────────────────
# Built-in Mode Definitions
# ──────────────────────────────────────────────────────────────

BUILT_IN_MODES: Dict[str, ModeProfile] = {
    ModeType.DEFAULT.value: ModeProfile(
        mode_type=ModeType.DEFAULT,
        display_name="Default",
        icon="🌐",
        description="Balanced mode — good at everything, no specific focus",
        color="cyan",
        primary_agent="general",
        agent_weights={"general": 1.0, "code_gen": 0.8, "debug": 0.8, "review": 0.6, "security": 0.5},
        system_prompt_addon="",
        reasoning_strategy="auto",
        reasoning_depth_modifier=0,
        creativity_modifier=0.0,
        tool_overrides={},
        custom_instructions="",
        focus_keywords=[],
        max_response_length=4096,
        enable_voice=None,
    ),
    ModeType.CODE.value: ModeProfile(
        mode_type=ModeType.CODE,
        display_name="Code Mode",
        icon="💻",
        description="Focused on code generation, refactoring, and implementation",
        color="green",
        primary_agent="code_gen",
        agent_weights={"code_gen": 1.5, "debug": 1.2, "review": 0.8, "general": 0.5, "security": 0.5},
        system_prompt_addon="""
You are in CODE MODE. Focus on:
- Writing clean, efficient, production-ready code
- Following best practices and design patterns
- Providing complete, runnable implementations
- Including error handling and edge cases
- Adding clear comments and documentation
Always prefer showing code over explaining theory.
""",
        reasoning_strategy="decompose",
        reasoning_depth_modifier=1,
        creativity_modifier=0.1,
        tool_overrides={"code_execute": True, "file_read": True, "file_write": True},
        custom_instructions="",
        focus_keywords=["code", "implement", "function", "class", "write", "create", "build", "program",
                        "script", "api", "endpoint", "component", "module", "library", "package",
                        "algorithm", "data structure", "refactor", "optimize"],
        max_response_length=8192,
        enable_voice=None,
    ),
    ModeType.RESEARCH.value: ModeProfile(
        mode_type=ModeType.RESEARCH,
        display_name="Research Mode",
        icon="🔬",
        description="Deep analysis, comparisons, and thorough investigation",
        color="blue",
        primary_agent="general",
        agent_weights={"general": 1.5, "review": 1.0, "security": 0.8, "code_gen": 0.5, "debug": 0.5},
        system_prompt_addon="""
You are in RESEARCH MODE. Focus on:
- Thorough, comprehensive analysis
- Multiple perspectives and viewpoints
- Citing reasoning and trade-offs
- Comparative analysis when relevant
- Structured responses with clear sections
- Deep dives into topics
Prioritize accuracy and depth over brevity.
""",
        reasoning_strategy="tree_of_thought",
        reasoning_depth_modifier=2,
        creativity_modifier=0.2,
        tool_overrides={"http_request": True},
        custom_instructions="",
        focus_keywords=["research", "analyze", "compare", "investigate", "study", "explore",
                        "pros and cons", "trade-off", "best practice", "architecture", "design",
                        "strategy", "approach", "methodology", "framework"],
        max_response_length=12000,
        enable_voice=None,
    ),
    ModeType.REVIEW.value: ModeProfile(
        mode_type=ModeType.REVIEW,
        display_name="Review Mode",
        icon="🔍",
        description="Code review, quality assessment, and optimization suggestions",
        color="yellow",
        primary_agent="review",
        agent_weights={"review": 1.5, "security": 1.2, "debug": 1.0, "code_gen": 0.6, "general": 0.5},
        system_prompt_addon="""
You are in REVIEW MODE. Focus on:
- Code quality and maintainability
- Performance bottlenecks and optimization
- Best practices violations
- Error handling gaps
- Test coverage suggestions
- Refactoring opportunities
- SOLID principles adherence
Rate severity: Critical > High > Medium > Low > Info
""",
        reasoning_strategy="reflexion",
        reasoning_depth_modifier=1,
        creativity_modifier=-0.1,
        tool_overrides={"file_read": True},
        custom_instructions="",
        focus_keywords=["review", "check", "audit", "quality", "improve", "optimize",
                        "performance", "clean", "refactor", "best practice", "lint",
                        "smell", "anti-pattern", "maintainability"],
        max_response_length=6000,
        enable_voice=None,
    ),
    ModeType.SECURITY.value: ModeProfile(
        mode_type=ModeType.SECURITY,
        display_name="Security Mode",
        icon="🛡️",
        description="Security analysis, vulnerability detection, and hardening",
        color="red",
        primary_agent="security",
        agent_weights={"security": 2.0, "review": 1.0, "debug": 0.8, "code_gen": 0.5, "general": 0.4},
        system_prompt_addon="""
You are in SECURITY MODE. Focus on:
- OWASP Top 10 vulnerabilities
- Input validation and sanitization
- Authentication and authorization flaws
- SQL injection, XSS, CSRF risks
- Dependency vulnerabilities
- Data exposure risks
- Encryption and secrets management
- Compliance (GDPR, HIPAA, SOC2)
Always assume adversarial intent. Rate findings by CVSS severity.
""",
        reasoning_strategy="chain_of_thought",
        reasoning_depth_modifier=2,
        creativity_modifier=-0.2,
        tool_overrides={"file_read": True, "file_search": True},
        custom_instructions="",
        focus_keywords=["security", "vulnerability", "exploit", "attack", "injection", "xss",
                        "csrf", "auth", "encryption", "hash", "password", "token", "secret",
                        "owasp", "pentest", "scan", "compliance", "gdpr", "hipaa"],
        max_response_length=8000,
        enable_voice=None,
    ),
    ModeType.DEBUG.value: ModeProfile(
        mode_type=ModeType.DEBUG,
        display_name="Debug Mode",
        icon="🐛",
        description="Error analysis, troubleshooting, and root cause investigation",
        color="magenta",
        primary_agent="debug",
        agent_weights={"debug": 2.0, "code_gen": 0.8, "review": 0.7, "general": 0.5, "security": 0.3},
        system_prompt_addon="""
You are in DEBUG MODE. Focus on:
- Systematic error analysis
- Stack trace interpretation
- Root cause identification
- Step-by-step troubleshooting
- Fix suggestions with explanations
- Prevention strategies
- Log analysis
Always ask for error messages, stack traces, and reproduction steps.
""",
        reasoning_strategy="chain_of_thought",
        reasoning_depth_modifier=1,
        creativity_modifier=0.0,
        tool_overrides={"terminal": True, "file_read": True, "code_execute": True},
        custom_instructions="",
        focus_keywords=["error", "bug", "fix", "crash", "exception", "traceback", "stack trace",
                        "not working", "fails", "broken", "issue", "problem", "debug",
                        "troubleshoot", "diagnose", "log"],
        max_response_length=6000,
        enable_voice=None,
    ),
    ModeType.CREATIVE.value: ModeProfile(
        mode_type=ModeType.CREATIVE,
        display_name="Creative Mode",
        icon="🎨",
        description="Creative writing, brainstorming, and ideation",
        color="bright_magenta",
        primary_agent="general",
        agent_weights={"general": 1.5, "code_gen": 0.7, "review": 0.3, "debug": 0.2, "security": 0.2},
        system_prompt_addon="""
You are in CREATIVE MODE. Focus on:
- Original, innovative ideas and approaches
- Brainstorming and divergent thinking
- Creative solutions to problems
- Engaging, well-structured writing
- Storytelling and narrative
Be bold, experimental, and imaginative. Don't hold back on creative suggestions.
""",
        reasoning_strategy="tree_of_thought",
        reasoning_depth_modifier=0,
        creativity_modifier=0.4,
        tool_overrides={},
        custom_instructions="",
        focus_keywords=["creative", "brainstorm", "idea", "innovate", "design", "story",
                        "write", "content", "blog", "article", "naming", "branding"],
        max_response_length=8000,
        enable_voice=None,
    ),
    ModeType.LEARNING.value: ModeProfile(
        mode_type=ModeType.LEARNING,
        display_name="Learning Mode",
        icon="📚",
        description="Teaching, explanations, and educational content",
        color="bright_cyan",
        primary_agent="general",
        agent_weights={"general": 1.5, "code_gen": 1.0, "review": 0.5, "debug": 0.5, "security": 0.3},
        system_prompt_addon="""
You are in LEARNING MODE. Focus on:
- Clear, beginner-friendly explanations
- Step-by-step breakdowns
- Real-world examples and analogies
- Visual representations when possible
- Building from fundamentals to advanced
- Practice exercises and challenges
- "Why" before "How"
Assume the user wants to deeply understand, not just get an answer.
""",
        reasoning_strategy="decompose",
        reasoning_depth_modifier=1,
        creativity_modifier=0.15,
        tool_overrides={},
        custom_instructions="",
        focus_keywords=["learn", "teach", "explain", "understand", "tutorial", "guide",
                        "how does", "what is", "why", "concept", "beginner", "basics"],
        max_response_length=10000,
        enable_voice=None,
    ),
    ModeType.DEVOPS.value: ModeProfile(
        mode_type=ModeType.DEVOPS,
        display_name="DevOps Mode",
        icon="⚙️",
        description="Infrastructure, CI/CD, deployment, and operations",
        color="bright_yellow",
        primary_agent="general",
        agent_weights={"general": 1.2, "code_gen": 1.0, "security": 0.8, "debug": 0.8, "review": 0.5},
        system_prompt_addon="""
You are in DEVOPS MODE. Focus on:
- Infrastructure as Code (Terraform, Docker, K8s)
- CI/CD pipelines (GitHub Actions, Jenkins)
- Monitoring and observability
- Deployment strategies
- Cloud services (AWS, Azure, GCP)
- Container orchestration
- Scripting and automation
Prefer practical, copy-paste-ready configs and scripts.
""",
        reasoning_strategy="decompose",
        reasoning_depth_modifier=1,
        creativity_modifier=0.0,
        tool_overrides={"terminal": True, "file_read": True, "file_write": True},
        custom_instructions="",
        focus_keywords=["deploy", "docker", "kubernetes", "k8s", "terraform", "ci/cd",
                        "pipeline", "aws", "azure", "gcp", "nginx", "server", "container",
                        "infrastructure", "devops", "monitoring", "helm"],
        max_response_length=6000,
        enable_voice=None,
    ),
    ModeType.CUSTOM.value: ModeProfile(
        mode_type=ModeType.CUSTOM,
        display_name="Custom Mode",
        icon="🎯",
        description="User-defined mode with custom instructions and behavior",
        color="bright_white",
        primary_agent="general",
        agent_weights={"general": 1.0, "code_gen": 1.0, "debug": 1.0, "review": 1.0, "security": 1.0},
        system_prompt_addon="",
        reasoning_strategy="auto",
        reasoning_depth_modifier=0,
        creativity_modifier=0.0,
        tool_overrides={},
        custom_instructions="",
        focus_keywords=[],
        max_response_length=8000,
        enable_voice=None,
    ),
}


class ModeManager:
    """
    Manages operational modes for ALD-01.
    Handles mode switching, custom mode creation, persistence, and mode-aware routing.
    """

    def __init__(self):
        self._current_mode: ModeType = ModeType.DEFAULT
        self._modes: Dict[str, ModeProfile] = dict(BUILT_IN_MODES)
        self._mode_history: List[Dict[str, Any]] = []
        self._scheduled_mode: Optional[Dict[str, Any]] = None
        self._persistence_path = os.path.join(CONFIG_DIR, "modes.json")
        self._load_custom_modes()
        self._load_current_mode()

    @property
    def current_mode(self) -> ModeProfile:
        """Get the current active mode profile."""
        return self._modes.get(self._current_mode.value, BUILT_IN_MODES[ModeType.DEFAULT.value])

    @property
    def current_mode_type(self) -> ModeType:
        return self._current_mode

    def switch_mode(self, mode_name: str) -> ModeProfile:
        """Switch to a different mode."""
        mode_name = mode_name.lower().strip()

        # Find matching mode
        if mode_name in self._modes:
            mode_key = mode_name
        else:
            # Try fuzzy match
            for key in self._modes:
                if mode_name in key or key in mode_name:
                    mode_key = key
                    break
            else:
                raise ValueError(
                    f"Unknown mode: '{mode_name}'. Available: {', '.join(self._modes.keys())}"
                )

        try:
            self._current_mode = ModeType(mode_key)
        except ValueError:
            self._current_mode = ModeType.CUSTOM

        self._mode_history.append({
            "mode": mode_key,
            "timestamp": time.time(),
            "display_name": self._modes[mode_key].display_name,
        })

        # Keep history bounded
        if len(self._mode_history) > 100:
            self._mode_history = self._mode_history[-100:]

        self._save_current_mode()
        logger.info(f"Mode switched to: {self._modes[mode_key].display_name}")
        return self._modes[mode_key]

    def set_custom_instructions(self, instructions: str) -> None:
        """Set custom instructions for the current mode."""
        mode = self.current_mode
        mode.custom_instructions = instructions
        self._save_custom_modes()

    def create_custom_mode(
        self,
        name: str,
        display_name: str,
        description: str,
        instructions: str,
        icon: str = "🎯",
        color: str = "white",
        primary_agent: str = "general",
        reasoning_strategy: str = "auto",
    ) -> ModeProfile:
        """Create a new custom mode."""
        mode = ModeProfile(
            mode_type=ModeType.CUSTOM,
            display_name=display_name,
            icon=icon,
            description=description,
            color=color,
            primary_agent=primary_agent,
            agent_weights={"general": 1.0, "code_gen": 1.0, "debug": 1.0, "review": 1.0, "security": 1.0},
            system_prompt_addon=f"\n{instructions}\n",
            reasoning_strategy=reasoning_strategy,
            reasoning_depth_modifier=0,
            creativity_modifier=0.0,
            tool_overrides={},
            custom_instructions=instructions,
            focus_keywords=[],
            max_response_length=8000,
            enable_voice=None,
            metadata={"user_created": True, "created_at": time.time()},
        )
        self._modes[name.lower()] = mode
        self._save_custom_modes()
        return mode

    def delete_custom_mode(self, name: str) -> bool:
        """Delete a custom mode (can't delete built-in)."""
        name = name.lower()
        if name in BUILT_IN_MODES:
            return False
        if name in self._modes:
            del self._modes[name]
            self._save_custom_modes()
            return True
        return False

    def get_mode_enhanced_prompt(self) -> str:
        """Get the current mode's system prompt addition."""
        mode = self.current_mode
        prompt_parts = []

        if mode.system_prompt_addon:
            prompt_parts.append(mode.system_prompt_addon)
        if mode.custom_instructions:
            prompt_parts.append(f"\n[User Custom Instructions]\n{mode.custom_instructions}")

        return "\n".join(prompt_parts)

    def get_agent_weight(self, agent_name: str) -> float:
        """Get the routing weight for an agent in the current mode."""
        return self.current_mode.agent_weights.get(agent_name, 1.0)

    def get_tool_override(self, tool_name: str) -> Optional[bool]:
        """Check if the current mode overrides a tool's enabled state."""
        return self.current_mode.tool_overrides.get(tool_name, None)

    def auto_detect_mode(self, query: str) -> Optional[str]:
        """Auto-detect the best mode for a query (for suggestions, not auto-switching)."""
        query_lower = query.lower()
        best_mode = None
        best_score = 0

        for name, mode in self._modes.items():
            if not mode.focus_keywords:
                continue
            score = sum(1 for kw in mode.focus_keywords if kw in query_lower)
            if score > best_score:
                best_score = score
                best_mode = name

        return best_mode if best_score >= 2 else None

    def list_modes(self) -> List[Dict[str, Any]]:
        """List all available modes with their details."""
        result = []
        for name, mode in self._modes.items():
            info = mode.to_dict()
            info["key"] = name
            info["active"] = (name == self._current_mode.value)
            info["built_in"] = name in BUILT_IN_MODES
            result.append(info)
        return result

    def get_mode_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent mode switch history."""
        return self._mode_history[-limit:]

    # ──────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────

    def _save_current_mode(self) -> None:
        """Persist current mode to disk."""
        try:
            data = self._load_persistence()
            data["current_mode"] = self._current_mode.value
            self._write_persistence(data)
        except Exception as e:
            logger.warning(f"Failed to save current mode: {e}")

    def _load_current_mode(self) -> None:
        """Load current mode from disk."""
        try:
            data = self._load_persistence()
            mode_value = data.get("current_mode", "default")
            try:
                self._current_mode = ModeType(mode_value)
            except ValueError:
                self._current_mode = ModeType.DEFAULT
        except Exception:
            self._current_mode = ModeType.DEFAULT

    def _save_custom_modes(self) -> None:
        """Save custom modes to disk."""
        try:
            data = self._load_persistence()
            custom = {}
            for name, mode in self._modes.items():
                if name not in BUILT_IN_MODES or mode.custom_instructions:
                    custom[name] = {
                        "display_name": mode.display_name,
                        "icon": mode.icon,
                        "description": mode.description,
                        "color": mode.color,
                        "primary_agent": mode.primary_agent,
                        "custom_instructions": mode.custom_instructions,
                        "reasoning_strategy": mode.reasoning_strategy,
                        "system_prompt_addon": mode.system_prompt_addon,
                        "metadata": mode.metadata,
                    }
            data["custom_modes"] = custom
            self._write_persistence(data)
        except Exception as e:
            logger.warning(f"Failed to save custom modes: {e}")

    def _load_custom_modes(self) -> None:
        """Load custom modes from disk."""
        try:
            data = self._load_persistence()
            customs = data.get("custom_modes", {})
            for name, cfg in customs.items():
                if name in BUILT_IN_MODES:
                    # Update custom instructions for built-in
                    self._modes[name].custom_instructions = cfg.get("custom_instructions", "")
                else:
                    # Create user-defined mode
                    self.create_custom_mode(
                        name=name,
                        display_name=cfg.get("display_name", name),
                        description=cfg.get("description", ""),
                        instructions=cfg.get("custom_instructions", ""),
                        icon=cfg.get("icon", "🎯"),
                        color=cfg.get("color", "white"),
                        primary_agent=cfg.get("primary_agent", "general"),
                        reasoning_strategy=cfg.get("reasoning_strategy", "auto"),
                    )
        except Exception:
            pass

    def _load_persistence(self) -> Dict[str, Any]:
        """Load persistence file."""
        if os.path.exists(self._persistence_path):
            try:
                with open(self._persistence_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _write_persistence(self, data: Dict[str, Any]) -> None:
        """Write persistence file."""
        os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
        with open(self._persistence_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


# Singleton
_mode_manager: Optional[ModeManager] = None


def get_mode_manager() -> ModeManager:
    """Get or create the global mode manager."""
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = ModeManager()
    return _mode_manager
