"""
ALD-01 Debug Agent
Expert in error analysis, troubleshooting, and root cause analysis.
"""

from ald01.agents.base import BaseAgent

DEBUG_KEYWORDS = [
    "debug", "error", "bug", "fix", "broken", "crash", "fail", "issue",
    "exception", "traceback", "stack trace", "not working", "wrong",
    "unexpected", "problem", "troubleshoot", "diagnose", "resolve",
    "undefined", "null", "nan", "segfault", "timeout", "memory leak",
    "import error", "syntax error", "type error", "runtime", "compile",
    "500", "404", "403", "connection refused", "cors", "permission denied",
]


class DebugAgent(BaseAgent):
    """Analyzes errors, finds root causes, and suggests targeted fixes."""

    def __init__(self):
        super().__init__(
            name="debug",
            display_name="Debug",
            expertise="Error analysis, debugging, troubleshooting, root cause analysis",
        )

    def _default_system_prompt(self) -> str:
        return """You are ALD-01's Debug Agent — an expert debugger and troubleshooter.

Your capabilities:
- Analyze error messages, stack traces, and log outputs
- Identify root causes of bugs and unexpected behavior
- Suggest targeted fixes with clear explanations
- Detect common pitfalls and anti-patterns
- Run diagnostic procedures when needed

Methodology:
1. OBSERVE: Read the error carefully, identify the type and location
2. HYPOTHESIZE: Form hypotheses about the root cause
3. NARROW DOWN: Eliminate possibilities systematically
4. FIX: Provide the exact fix with explanation
5. PREVENT: Suggest how to prevent similar issues

Guidelines:
- Always explain WHY the error occurred, not just how to fix it
- Provide the corrected code, not just descriptions
- Consider edge cases and related issues
- Suggest preventive measures (tests, validations, etc.)
- If uncertain, list the top 3 most likely causes"""

    def matches(self, query: str) -> float:
        query_lower = query.lower()
        score = 0.0
        for kw in DEBUG_KEYWORDS:
            if kw in query_lower:
                score += 0.2
        if any(phrase in query_lower for phrase in ["not working", "getting error", "help me fix", "why is"]):
            score += 0.3
        # Stack trace detection
        if "traceback" in query_lower or "at line" in query_lower or "error:" in query_lower:
            score += 0.4
        return min(score, 1.0)
