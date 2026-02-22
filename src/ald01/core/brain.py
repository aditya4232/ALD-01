"""
ALD-01 AGI Brain
Neural skill tracking, memory visualization, and self-learning system.
Tracks skills learned, reasoning patterns, memory connections, and neural growth.
Provides data for the Brain Visualization page in the dashboard.
"""

import os
import time
import json
import math
import random
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.brain")


@dataclass
class NeuralNode:
    """A node in ALD's neural network visualization."""
    id: str
    label: str
    category: str  # 'skill', 'memory', 'reasoning', 'aptitude', 'knowledge', 'tool', 'language'
    strength: float = 0.0  # 0.0 to 1.0
    activation_count: int = 0
    last_activated: float = 0.0
    position: Tuple[float, float] = (0.0, 0.0)  # x, y for visualization
    color: str = "#00ffff"
    size: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "category": self.category,
            "strength": round(self.strength, 3),
            "activation_count": self.activation_count,
            "last_activated": self.last_activated,
            "position": {"x": self.position[0], "y": self.position[1]},
            "color": self.color,
            "size": round(self.size, 2),
            "metadata": self.metadata,
        }


@dataclass
class NeuralConnection:
    """A connection between neural nodes."""
    from_id: str
    to_id: str
    weight: float = 0.0  # 0.0 to 1.0
    activation_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "weight": round(self.weight, 3),
            "activations": self.activation_count,
        }


# Category colors for visualization
CATEGORY_COLORS = {
    "skill": "#00ff88",       # Green
    "memory": "#00ccff",      # Cyan
    "reasoning": "#ff6600",   # Orange
    "aptitude": "#ff00ff",    # Magenta
    "knowledge": "#ffff00",   # Yellow
    "tool": "#00ffcc",        # Teal
    "language": "#ff4488",    # Pink
    "personality": "#aa88ff", # Purple
    "learning": "#88ff00",    # Lime
}


class AGIBrain:
    """
    ALD-01's AGI Brain — tracks neural growth, skills, memory, and reasoning.
    
    Provides:
    - Neural network visualization data (nodes + connections)
    - Skill tracking and strength
    - Memory dot visualization
    - Reasoning pattern tracking
    - Self-learning metrics
    - Aptitude scores
    - Knowledge graph
    """

    def __init__(self):
        self._nodes: Dict[str, NeuralNode] = {}
        self._connections: List[NeuralConnection] = []
        self._skills_learned: Dict[str, float] = {}
        self._reasoning_patterns: Dict[str, int] = defaultdict(int)
        self._aptitude_scores: Dict[str, float] = {}
        self._knowledge_areas: Dict[str, float] = {}
        self._total_activations: int = 0
        self._growth_history: List[Dict[str, Any]] = []
        self._persistence_path = os.path.join(CONFIG_DIR, "brain.json")
        self._initialize_core_nodes()
        self._load()

    def _initialize_core_nodes(self) -> None:
        """Initialize the core neural structure."""
        core_nodes = [
            # Core reasoning
            ("reasoning_cot", "Chain of Thought", "reasoning", 0.5),
            ("reasoning_tot", "Tree of Thought", "reasoning", 0.3),
            ("reasoning_reflexion", "Reflexion", "reasoning", 0.3),
            ("reasoning_decompose", "Decomposition", "reasoning", 0.4),
            ("reasoning_analogy", "Analogical Reasoning", "reasoning", 0.2),
            ("reasoning_causal", "Causal Reasoning", "reasoning", 0.2),

            # Core skills
            ("skill_python", "Python", "skill", 0.0),
            ("skill_javascript", "JavaScript", "skill", 0.0),
            ("skill_web", "Web Development", "skill", 0.0),
            ("skill_api", "API Design", "skill", 0.0),
            ("skill_database", "Databases", "skill", 0.0),
            ("skill_devops", "DevOps", "skill", 0.0),
            ("skill_security", "Security", "skill", 0.0),
            ("skill_testing", "Testing", "skill", 0.0),
            ("skill_debugging", "Debugging", "skill", 0.0),
            ("skill_architecture", "Architecture", "skill", 0.0),
            ("skill_ml", "Machine Learning", "skill", 0.0),
            ("skill_data", "Data Science", "skill", 0.0),
            ("skill_mobile", "Mobile Dev", "skill", 0.0),
            ("skill_cloud", "Cloud Computing", "skill", 0.0),
            ("skill_linux", "Linux/CLI", "skill", 0.0),

            # Aptitudes
            ("aptitude_logic", "Logical Thinking", "aptitude", 0.5),
            ("aptitude_creativity", "Creativity", "aptitude", 0.3),
            ("aptitude_math", "Mathematics", "aptitude", 0.3),
            ("aptitude_communication", "Communication", "aptitude", 0.4),
            ("aptitude_problem_solving", "Problem Solving", "aptitude", 0.4),
            ("aptitude_memory", "Memory Recall", "aptitude", 0.5),
            ("aptitude_speed", "Processing Speed", "aptitude", 0.5),
            ("aptitude_accuracy", "Accuracy", "aptitude", 0.4),

            # Memory types
            ("memory_short", "Short-term Memory", "memory", 0.5),
            ("memory_long", "Long-term Memory", "memory", 0.3),
            ("memory_semantic", "Semantic Memory", "memory", 0.3),
            ("memory_episodic", "Episodic Memory", "memory", 0.2),
            ("memory_procedural", "Procedural Memory", "memory", 0.2),

            # Tools
            ("tool_filesystem", "File System", "tool", 0.0),
            ("tool_terminal", "Terminal", "tool", 0.0),
            ("tool_code_exec", "Code Execution", "tool", 0.0),
            ("tool_http", "HTTP Requests", "tool", 0.0),
            ("tool_clipboard", "Clipboard", "tool", 0.0),

            # Languages
            ("lang_english", "English", "language", 0.8),
            ("lang_hindi", "Hindi", "language", 0.0),
            ("lang_hinglish", "Hinglish", "language", 0.0),

            # Personality
            ("personality_helpful", "Helpfulness", "personality", 0.7),
            ("personality_professional", "Professionalism", "personality", 0.6),
            ("personality_humor", "Humor", "personality", 0.2),
            ("personality_empathy", "Empathy", "personality", 0.3),
        ]

        for node_id, label, category, strength in core_nodes:
            if node_id not in self._nodes:
                x = random.uniform(-5, 5)
                y = random.uniform(-5, 5)
                self._nodes[node_id] = NeuralNode(
                    id=node_id,
                    label=label,
                    category=category,
                    strength=strength,
                    color=CATEGORY_COLORS.get(category, "#ffffff"),
                    position=(round(x, 2), round(y, 2)),
                    size=max(0.5, strength * 2),
                )

        # Create initial connections between related nodes
        core_connections = [
            ("reasoning_cot", "aptitude_logic", 0.6),
            ("reasoning_tot", "aptitude_creativity", 0.5),
            ("reasoning_decompose", "aptitude_problem_solving", 0.6),
            ("aptitude_logic", "aptitude_math", 0.4),
            ("aptitude_problem_solving", "skill_debugging", 0.3),
            ("skill_python", "skill_testing", 0.2),
            ("skill_python", "skill_ml", 0.2),
            ("skill_web", "skill_javascript", 0.4),
            ("skill_api", "skill_web", 0.3),
            ("skill_database", "skill_api", 0.3),
            ("skill_devops", "skill_cloud", 0.4),
            ("skill_security", "aptitude_logic", 0.3),
            ("memory_short", "memory_long", 0.5),
            ("memory_semantic", "memory_long", 0.4),
            ("lang_english", "aptitude_communication", 0.6),
            ("lang_hindi", "lang_hinglish", 0.7),
            ("lang_english", "lang_hinglish", 0.5),
        ]
        existing_conns = {(c.from_id, c.to_id) for c in self._connections}
        for from_id, to_id, weight in core_connections:
            if (from_id, to_id) not in existing_conns:
                self._connections.append(NeuralConnection(from_id, to_id, weight))

    def activate_skill(self, skill_id: str, intensity: float = 0.1) -> None:
        """Activate a skill node — strengthens it over time."""
        if skill_id not in self._nodes:
            # Auto-create new skill node
            self._nodes[skill_id] = NeuralNode(
                id=skill_id,
                label=skill_id.replace("skill_", "").replace("_", " ").title(),
                category="skill",
                color=CATEGORY_COLORS["skill"],
                position=(random.uniform(-5, 5), random.uniform(-5, 5)),
            )

        node = self._nodes[skill_id]
        node.activation_count += 1
        node.last_activated = time.time()
        # Strength grows but has diminishing returns (sigmoid-like)
        node.strength = min(1.0, node.strength + intensity * (1 - node.strength))
        node.size = max(0.5, node.strength * 2.5)
        self._total_activations += 1

    def activate_reasoning(self, pattern: str) -> None:
        """Record a reasoning pattern activation."""
        self._reasoning_patterns[pattern] += 1
        node_id = f"reasoning_{pattern}"
        if node_id in self._nodes:
            self.activate_skill(node_id, 0.05)

    def activate_tool(self, tool_name: str) -> None:
        """Record tool usage."""
        node_id = f"tool_{tool_name}"
        self.activate_skill(node_id, 0.05)

    def learn_topic(self, topic: str, depth: float = 0.1) -> None:
        """Learn about a topic — adds or strengthens knowledge."""
        node_id = f"knowledge_{topic.lower().replace(' ', '_')}"

        if node_id not in self._nodes:
            self._nodes[node_id] = NeuralNode(
                id=node_id,
                label=topic.title(),
                category="knowledge",
                color=CATEGORY_COLORS["knowledge"],
                position=(random.uniform(-5, 5), random.uniform(-5, 5)),
            )

        self.activate_skill(node_id, depth)

        # Create connections to related skills
        topic_lower = topic.lower()
        skill_keywords = {
            "python": "skill_python", "javascript": "skill_javascript",
            "web": "skill_web", "api": "skill_api", "database": "skill_database",
            "security": "skill_security", "test": "skill_testing",
            "debug": "skill_debugging", "ml": "skill_ml", "data": "skill_data",
            "cloud": "skill_cloud", "docker": "skill_devops", "linux": "skill_linux",
        }
        for kw, skill_id in skill_keywords.items():
            if kw in topic_lower:
                self._strengthen_connection(node_id, skill_id, 0.05)

    def enable_language(self, language: str) -> None:
        """Enable a language pack."""
        node_id = f"lang_{language.lower()}"
        if node_id in self._nodes:
            self._nodes[node_id].strength = max(self._nodes[node_id].strength, 0.5)
            self._nodes[node_id].metadata["enabled"] = True

    def _strengthen_connection(self, from_id: str, to_id: str, amount: float = 0.05) -> None:
        """Strengthen or create a connection."""
        for conn in self._connections:
            if conn.from_id == from_id and conn.to_id == to_id:
                conn.weight = min(1.0, conn.weight + amount)
                conn.activation_count += 1
                return
        self._connections.append(NeuralConnection(from_id, to_id, amount, 1))

    def get_brain_state(self) -> Dict[str, Any]:
        """Get the complete brain state for visualization."""
        # Calculate overall brain power
        all_strengths = [n.strength for n in self._nodes.values()]
        avg_strength = sum(all_strengths) / max(len(all_strengths), 1)

        # Category breakdowns
        categories = defaultdict(list)
        for node in self._nodes.values():
            categories[node.category].append(node.strength)

        category_avg = {}
        for cat, strengths in categories.items():
            category_avg[cat] = round(sum(strengths) / max(len(strengths), 1), 3)

        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "connections": [c.to_dict() for c in self._connections if c.weight > 0.01],
            "total_nodes": len(self._nodes),
            "total_connections": len(self._connections),
            "total_activations": self._total_activations,
            "overall_brain_power": round(avg_strength * 100, 1),
            "category_strength": category_avg,
            "top_skills": self._get_top_skills(10),
            "reasoning_patterns": dict(self._reasoning_patterns),
            "growth_history": self._growth_history[-50:],
        }

    def _get_top_skills(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N strongest skills."""
        skills = [(node.label, node.strength, node.activation_count)
                  for node in self._nodes.values()
                  if node.category == "skill" and node.strength > 0]
        skills.sort(key=lambda x: x[1], reverse=True)
        return [{"name": s[0], "strength": round(s[1], 3), "activations": s[2]} for s in skills[:n]]

    def get_aptitude_scores(self) -> Dict[str, float]:
        """Get all aptitude scores."""
        return {
            node.label: round(node.strength, 3)
            for node in self._nodes.values()
            if node.category == "aptitude"
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get brain statistics."""
        return {
            "total_nodes": len(self._nodes),
            "total_connections": len(self._connections),
            "total_activations": self._total_activations,
            "skills_count": sum(1 for n in self._nodes.values() if n.category == "skill" and n.strength > 0),
            "reasoning_patterns": len(self._reasoning_patterns),
            "knowledge_areas": sum(1 for n in self._nodes.values() if n.category == "knowledge"),
            "languages": [n.label for n in self._nodes.values() if n.category == "language" and n.strength > 0],
        }

    def record_growth(self) -> None:
        """Record a growth snapshot for history."""
        all_strengths = [n.strength for n in self._nodes.values()]
        self._growth_history.append({
            "timestamp": time.time(),
            "avg_strength": round(sum(all_strengths) / max(len(all_strengths), 1), 4),
            "total_nodes": len(self._nodes),
            "total_activations": self._total_activations,
        })
        if len(self._growth_history) > 200:
            self._growth_history = self._growth_history[-200:]

    def save(self) -> None:
        """Persist brain state."""
        try:
            data = {
                "nodes": {nid: {
                    "label": n.label, "category": n.category, "strength": n.strength,
                    "activation_count": n.activation_count, "last_activated": n.last_activated,
                    "position": n.position, "metadata": n.metadata,
                } for nid, n in self._nodes.items()},
                "connections": [
                    {"from": c.from_id, "to": c.to_id, "weight": c.weight, "activations": c.activation_count}
                    for c in self._connections
                ],
                "reasoning_patterns": dict(self._reasoning_patterns),
                "total_activations": self._total_activations,
                "growth_history": self._growth_history[-100:],
                "saved_at": time.time(),
            }
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save brain state: {e}")

    def _load(self) -> None:
        """Load brain state."""
        try:
            if not os.path.exists(self._persistence_path):
                return
            with open(self._persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for nid, nd in data.get("nodes", {}).items():
                if nid in self._nodes:
                    node = self._nodes[nid]
                    node.strength = nd.get("strength", node.strength)
                    node.activation_count = nd.get("activation_count", 0)
                    node.last_activated = nd.get("last_activated", 0)
                    node.size = max(0.5, node.strength * 2.5)
                    node.metadata = nd.get("metadata", {})
                    if nd.get("position"):
                        node.position = tuple(nd["position"])

            for cd in data.get("connections", []):
                existing = {(c.from_id, c.to_id) for c in self._connections}
                if (cd["from"], cd["to"]) not in existing:
                    self._connections.append(NeuralConnection(
                        cd["from"], cd["to"], cd.get("weight", 0), cd.get("activations", 0)
                    ))
                else:
                    for c in self._connections:
                        if c.from_id == cd["from"] and c.to_id == cd["to"]:
                            c.weight = cd.get("weight", c.weight)
                            c.activation_count = cd.get("activations", c.activation_count)

            self._reasoning_patterns = defaultdict(int, data.get("reasoning_patterns", {}))
            self._total_activations = data.get("total_activations", 0)
            self._growth_history = data.get("growth_history", [])

        except Exception as e:
            logger.warning(f"Failed to load brain state: {e}")


_brain: Optional[AGIBrain] = None

def get_brain() -> AGIBrain:
    global _brain
    if _brain is None:
        _brain = AGIBrain()
    return _brain
