"""
ALD-01 Code Generation Agent
Expert in writing code across 50+ languages.
"""

from ald01.agents.base import BaseAgent

# Keywords that trigger this agent
CODE_KEYWORDS = [
    "code", "write", "create", "build", "implement", "function", "class",
    "script", "program", "app", "api", "server", "component", "module",
    "generate", "scaffold", "boilerplate", "template", "html", "css", "js",
    "python", "javascript", "typescript", "java", "rust", "go", "c++",
    "react", "vue", "angular", "django", "flask", "fastapi", "express",
    "database", "sql", "query", "schema", "migration", "docker", "yaml",
    "config", "setup", "install", "package", "library", "framework",
    "frontend", "backend", "fullstack", "website", "webpage", "landing",
]


class CodeGenAgent(BaseAgent):
    """Generates code in any language from natural language descriptions."""

    def __init__(self):
        super().__init__(
            name="code_gen",
            display_name="CodeGen",
            expertise="Code generation, scaffolding, software development",
        )

    def _default_system_prompt(self) -> str:
        return """You are ALD-01's Code Generation Agent — an elite software engineer.

Your capabilities:
- Generate production-quality code in 50+ programming languages
- Create complete project scaffolds and boilerplate
- Write APIs, database schemas, configurations, tests
- Follow best practices: clean code, SOLID principles, proper error handling
- Provide clear comments and documentation

Guidelines:
- Always use modern, idiomatic patterns for the target language
- Include error handling and input validation
- Add type hints/annotations where applicable
- Structure code for maintainability and reusability
- When creating files, include proper imports and dependencies
- If creating a project, provide the full directory structure

You produce working, production-ready code — not pseudocode or snippets."""

    def matches(self, query: str) -> float:
        """Score how well this agent matches the query."""
        query_lower = query.lower()
        score = 0.0
        for kw in CODE_KEYWORDS:
            if kw in query_lower:
                score += 0.15
        # Strong signals
        if any(phrase in query_lower for phrase in ["write code", "create a", "build a", "implement", "generate"]):
            score += 0.3
        if any(lang in query_lower for lang in ["python", "javascript", "typescript", "java", "html", "react"]):
            score += 0.2
        return min(score, 1.0)
