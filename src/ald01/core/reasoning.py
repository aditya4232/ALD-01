"""
ALD-01 Reasoning Engine
Advanced multi-step reasoning with chain-of-thought, planning, and self-correction.
Enables AGI-like behavior for complex problem solving.
"""

import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ald01.config import get_config, get_brain_power_preset
from ald01.core.events import get_event_bus, Event, EventType
from ald01.core.memory import get_memory

logger = logging.getLogger("ald01.reasoning")


@dataclass
class ThoughtStep:
    """A single step in the reasoning chain."""
    step_number: int
    step_type: str  # 'observe', 'analyze', 'hypothesize', 'plan', 'evaluate', 'conclude'
    content: str
    confidence: float = 0.0  # 0.0 to 1.0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "type": self.step_type,
            "content": self.content,
            "confidence": round(self.confidence, 2),
            "duration_ms": round(self.duration_ms, 1),
            "metadata": self.metadata,
        }


@dataclass
class ReasoningChain:
    """A complete chain of thought reasoning process."""
    id: str
    query: str
    steps: List[ThoughtStep] = field(default_factory=list)
    conclusion: str = ""
    overall_confidence: float = 0.0
    total_duration_ms: float = 0.0
    strategy: str = "chain_of_thought"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "strategy": self.strategy,
            "steps": [s.to_dict() for s in self.steps],
            "conclusion": self.conclusion,
            "confidence": round(self.overall_confidence, 2),
            "total_duration_ms": round(self.total_duration_ms, 1),
            "step_count": len(self.steps),
        }


class ReasoningEngine:
    """
    Multi-strategy reasoning engine for complex problem solving.
    
    Strategies:
    - chain_of_thought: Step-by-step logical reasoning
    - tree_of_thought: Explore multiple reasoning paths
    - reflexion: Iterate and self-correct
    - decompose: Break complex problems into sub-problems
    """

    def __init__(self):
        self._config = get_config()
        self._event_bus = get_event_bus()
        self._memory = get_memory()
        self._chains: List[ReasoningChain] = []

    def get_reasoning_depth(self) -> int:
        """Get reasoning depth based on brain power level."""
        brain = get_brain_power_preset(self._config.brain_power)
        return brain["reasoning_depth"]

    async def build_reasoning_prompt(
        self,
        query: str,
        strategy: str = "auto",
        context: Optional[str] = None,
    ) -> str:
        """
        Build a reasoning-enhanced prompt based on strategy and brain power.
        Returns the enhanced system prompt to inject into the LLM call.
        """
        depth = self.get_reasoning_depth()

        if strategy == "auto":
            strategy = self._select_strategy(query, depth)

        chain = ReasoningChain(
            id=f"reason_{int(time.time()*1000)}",
            query=query,
            strategy=strategy,
        )

        await self._event_bus.emit(Event(
            type=EventType.THINKING_STARTED,
            data={"strategy": strategy, "depth": depth, "query": query[:80]},
            source="reasoning",
        ))

        # Build strategy-specific prompt
        if strategy == "chain_of_thought":
            prompt = self._build_cot_prompt(query, depth, context)
        elif strategy == "tree_of_thought":
            prompt = self._build_tot_prompt(query, depth, context)
        elif strategy == "reflexion":
            prompt = self._build_reflexion_prompt(query, depth, context)
        elif strategy == "decompose":
            prompt = self._build_decompose_prompt(query, depth, context)
        else:
            prompt = self._build_cot_prompt(query, depth, context)

        # Log thinking
        step = ThoughtStep(
            step_number=1,
            step_type="plan",
            content=f"Selected strategy: {strategy} at depth {depth}",
            confidence=0.8,
        )
        chain.steps.append(step)

        self._memory.log_thinking(
            thought_type=f"strategy_{strategy}",
            content=f"Reasoning with {strategy} (depth={depth}) for: {query[:100]}",
            depth=depth,
        )

        self._chains.append(chain)
        if len(self._chains) > 100:
            self._chains = self._chains[-100:]

        return prompt

    def _select_strategy(self, query: str, depth: int) -> str:
        """Auto-select the best reasoning strategy."""
        query_lower = query.lower()

        # Complex problem indicators
        if any(w in query_lower for w in ["compare", "pros and cons", "trade-off", "versus", "which is better"]):
            return "tree_of_thought"
        if any(w in query_lower for w in ["step by step", "how to", "explain", "walk me through"]):
            return "chain_of_thought"
        if any(w in query_lower for w in ["improve", "better", "optimize", "refactor", "review"]):
            return "reflexion"
        if any(w in query_lower for w in ["build", "create", "implement", "design", "architect"]):
            return "decompose"

        # Depth-based fallback
        if depth >= 7:
            return "tree_of_thought"
        elif depth >= 4:
            return "chain_of_thought"
        return "chain_of_thought"

    def _build_cot_prompt(self, query: str, depth: int, context: Optional[str]) -> str:
        """Build Chain-of-Thought reasoning prompt."""
        prompt = """Think through this step by step:

<reasoning>
Step 1: Understand the problem — what is being asked?
Step 2: Identify key requirements and constraints
Step 3: Consider relevant knowledge and approaches"""

        if depth >= 3:
            prompt += """
Step 4: Evaluate potential solutions
Step 5: Choose the best approach and justify why"""

        if depth >= 5:
            prompt += """
Step 6: Consider edge cases and potential issues
Step 7: Plan implementation details"""

        if depth >= 7:
            prompt += """
Step 8: Think about scalability and maintainability
Step 9: Consider alternative approaches you rejected and why
Step 10: Final review and quality check"""

        prompt += """
</reasoning>

After reasoning, provide your answer clearly and directly."""

        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        return prompt

    def _build_tot_prompt(self, query: str, depth: int, context: Optional[str]) -> str:
        """Build Tree-of-Thought reasoning prompt."""
        prompt = """Explore multiple approaches to this problem:

<tree_of_thought>
BRANCH A — First Approach:
- What: [describe approach]
- Pros: [advantages]
- Cons: [disadvantages]
- Confidence: [0-100%]

BRANCH B — Alternative Approach:
- What: [describe approach]
- Pros: [advantages]
- Cons: [disadvantages]
- Confidence: [0-100%]"""

        if depth >= 5:
            prompt += """

BRANCH C — Creative/Unconventional Approach:
- What: [describe approach]
- Pros: [advantages]
- Cons: [disadvantages]
- Confidence: [0-100%]"""

        prompt += """

EVALUATION:
- Best approach: [which branch and why]
- Key trade-offs: [what you're optimizing for]
</tree_of_thought>

Now provide your recommended solution based on the best approach."""

        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        return prompt

    def _build_reflexion_prompt(self, query: str, depth: int, context: Optional[str]) -> str:
        """Build Reflexion (self-correction) prompt."""
        prompt = """Solve this problem using iterative refinement:

<reflexion>
ATTEMPT 1:
- Initial solution/response
- Self-critique: What's wrong or could be improved?

ATTEMPT 2 (refined):
- Improved solution addressing the critique
- Self-critique: Any remaining issues?"""

        if depth >= 6:
            prompt += """

ATTEMPT 3 (final):
- Final refined solution
- Confidence assessment: How confident are you in this answer?
- Remaining uncertainties or caveats"""

        prompt += """
</reflexion>

Present your final, refined answer."""

        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        return prompt

    def _build_decompose_prompt(self, query: str, depth: int, context: Optional[str]) -> str:
        """Build problem decomposition prompt."""
        prompt = """Break this complex task into manageable sub-tasks:

<decomposition>
OVERALL GOAL: [restate the objective clearly]

SUB-TASKS:
1. [First sub-task] — Dependencies: none
2. [Second sub-task] — Dependencies: [which sub-tasks must be done first]
3. [Third sub-task] — Dependencies: [...]"""

        if depth >= 5:
            prompt += """
4. [Fourth sub-task]
5. [Fifth sub-task]

EXECUTION ORDER: [optimal sequence considering dependencies]
ESTIMATED COMPLEXITY: [simple/moderate/complex for each]"""

        if depth >= 7:
            prompt += """

RISKS AND MITIGATIONS:
- Risk 1: [potential issue] → Mitigation: [how to handle]
- Risk 2: [potential issue] → Mitigation: [how to handle]

VALIDATION CRITERIA:
- How to verify each sub-task is done correctly"""

        prompt += """
</decomposition>

Now solve each sub-task in order, providing the complete solution."""

        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        return prompt

    def get_recent_chains(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent reasoning chains."""
        return [c.to_dict() for c in self._chains[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning engine statistics."""
        strategies = {}
        for c in self._chains:
            strategies[c.strategy] = strategies.get(c.strategy, 0) + 1
        return {
            "total_chains": len(self._chains),
            "current_depth": self.get_reasoning_depth(),
            "strategies_used": strategies,
        }


# Singleton
_reasoning_engine: Optional[ReasoningEngine] = None


def get_reasoning_engine() -> ReasoningEngine:
    """Get or create the global reasoning engine."""
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine
