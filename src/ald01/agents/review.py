"""
ALD-01 Code Review Agent
Expert in code quality, security analysis, and best practices enforcement.
"""

from ald01.agents.base import BaseAgent

REVIEW_KEYWORDS = [
    "review", "analyze", "quality", "improve", "optimize", "refactor",
    "best practice", "clean code", "solid", "pattern", "anti-pattern",
    "performance", "efficiency", "readability", "maintainability",
    "code smell", "technical debt", "complexity", "coverage", "lint",
    "style", "convention", "standard", "benchmark", "profile",
    "look at this code", "check this", "what do you think",
]


class ReviewAgent(BaseAgent):
    """Comprehensive code review with quality scoring and actionable feedback."""

    def __init__(self):
        super().__init__(
            name="review",
            display_name="Review",
            expertise="Code review, quality analysis, performance optimization",
        )

    def _default_system_prompt(self) -> str:
        return """You are ALD-01's Code Review Agent — a senior software architect and code quality expert.

Your capabilities:
- Perform comprehensive code reviews with actionable feedback
- Identify security vulnerabilities and anti-patterns
- Assess code quality across multiple dimensions
- Suggest performance optimizations
- Enforce best practices and coding standards

Review Dimensions:
1. **Correctness**: Does it work as intended? Edge cases handled?
2. **Security**: Input validation, injection risks, data exposure?
3. **Performance**: Time/space complexity, unnecessary operations?
4. **Readability**: Clear naming, good structure, adequate comments?
5. **Maintainability**: SOLID principles, DRY, proper abstraction?
6. **Testing**: Test coverage, edge cases, error scenarios?

Output Format:
- Overall Score: X/10
- Category Scores
- Critical Issues (must fix)
- Suggestions (should fix)
- Positive Observations (what's done well)
- Refactored Code (if applicable)"""

    def matches(self, query: str) -> float:
        query_lower = query.lower()
        score = 0.0
        for kw in REVIEW_KEYWORDS:
            if kw in query_lower:
                score += 0.15
        if any(phrase in query_lower for phrase in ["review this", "check this code", "improve this"]):
            score += 0.4
        return min(score, 1.0)
