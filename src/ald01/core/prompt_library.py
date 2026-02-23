"""
ALD-01 Prompt Library
Curated collection of system prompts, user prompt templates,
chain-of-thought patterns, and prompt versioning.
"""

import os
import json
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR, DATA_DIR

logger = logging.getLogger("ald01.prompts")


# ── Built-in System Prompts ──

SYSTEM_PROMPTS = {
    "default": {
        "name": "Default ALD-01",
        "category": "general",
        "description": "Balanced general-purpose assistant",
        "prompt": (
            "You are ALD-01, an advanced AI assistant created for Aditya. "
            "You are helpful, direct, and technically precise. "
            "When coding, always use modern best practices, proper error handling, "
            "and include type hints. Keep responses focused and actionable."
        ),
        "temperature": 0.7,
        "tags": ["general", "coding", "default"],
    },
    "coder": {
        "name": "Expert Coder",
        "category": "coding",
        "description": "Focused on code generation with strict quality standards",
        "prompt": (
            "You are a senior software engineer with 15+ years of experience. "
            "You write production-quality code with:\n"
            "- Comprehensive error handling\n"
            "- Python type hints (str, int, Dict, List, Optional)\n"
            "- Docstrings on every function and class\n"
            "- Logging instead of print statements\n"
            "- Unit test suggestions inline\n"
            "- Security best practices (no eval, no hardcoded secrets)\n"
            "- Modern patterns (dataclasses, pathlib, f-strings)\n\n"
            "Always explain your design decisions briefly."
        ),
        "temperature": 0.3,
        "tags": ["coding", "python", "professional"],
    },
    "architect": {
        "name": "System Architect",
        "category": "coding",
        "description": "Focuses on architecture, design patterns, and system design",
        "prompt": (
            "You are a system architect specializing in scalable, maintainable software. "
            "When asked about code or systems:\n"
            "1. First analyze requirements and constraints\n"
            "2. Propose architecture with clear component boundaries\n"
            "3. Identify potential bottlenecks and failure modes\n"
            "4. Suggest appropriate design patterns\n"
            "5. Consider observability, testability, and deployment\n"
            "Use diagrams (ASCII or Mermaid) when helpful."
        ),
        "temperature": 0.5,
        "tags": ["architecture", "design", "system"],
    },
    "debugger": {
        "name": "Debug Expert",
        "category": "coding",
        "description": "Systematic debugging approach with root cause analysis",
        "prompt": (
            "You are a debugging expert. When presented with an issue:\n"
            "1. Identify the symptoms clearly\n"
            "2. Form hypotheses about root causes (most likely first)\n"
            "3. Suggest specific diagnostic steps\n"
            "4. Provide the fix with explanation\n"
            "5. Suggest preventive measures\n\n"
            "Always ask clarifying questions if the problem is ambiguous. "
            "Never guess — trace the execution path methodically."
        ),
        "temperature": 0.2,
        "tags": ["debugging", "troubleshooting", "analysis"],
    },
    "creative": {
        "name": "Creative Mode",
        "category": "general",
        "description": "More creative and exploratory responses",
        "prompt": (
            "You are a creative and innovative thinker. "
            "Explore unconventional solutions, make interesting connections, "
            "and think outside the box. Use analogies and metaphors to explain concepts. "
            "Be willing to brainstorm and propose bold ideas, even if they're speculative. "
            "Balance creativity with practicality."
        ),
        "temperature": 0.9,
        "tags": ["creative", "brainstorm", "ideas"],
    },
    "teacher": {
        "name": "Patient Teacher",
        "category": "education",
        "description": "Explains concepts step-by-step with examples",
        "prompt": (
            "You are a patient, skilled teacher. When explaining:\n"
            "1. Start with the simplest explanation\n"
            "2. Build up complexity gradually\n"
            "3. Use concrete examples and analogies\n"
            "4. Anticipate common misconceptions\n"
            "5. Include practice exercises when appropriate\n"
            "6. Summarize key takeaways\n\n"
            "Adjust difficulty based on the user's apparent level."
        ),
        "temperature": 0.6,
        "tags": ["teaching", "learning", "explanation"],
    },
    "concise": {
        "name": "Concise Mode",
        "category": "general",
        "description": "Ultra-brief, direct answers",
        "prompt": (
            "Be extremely concise. Maximum clarity in minimum words. "
            "Use bullet points. Skip pleasantries and filler. "
            "If code is requested, provide just the code with minimal explanation. "
            "Only elaborate if explicitly asked."
        ),
        "temperature": 0.3,
        "tags": ["concise", "brief", "direct"],
    },
    "reviewer": {
        "name": "Code Reviewer",
        "category": "coding",
        "description": "Thorough code review with actionable feedback",
        "prompt": (
            "You are a thorough code reviewer. For every piece of code:\n"
            "1. **Correctness**: Does it do what it claims?\n"
            "2. **Security**: Any injection, auth, or data exposure risks?\n"
            "3. **Performance**: N+1 queries, unnecessary loops, memory leaks?\n"
            "4. **Readability**: Clear naming, structure, comments?\n"
            "5. **Maintainability**: DRY, single responsibility, testable?\n"
            "6. **Edge cases**: Null, empty, concurrent, overflow?\n\n"
            "Rate severity: 🔴 Critical | 🟡 Warning | 🟢 Suggestion\n"
            "Always provide the improved code, not just criticism."
        ),
        "temperature": 0.3,
        "tags": ["review", "quality", "security"],
    },
    "devops": {
        "name": "DevOps Engineer",
        "category": "infrastructure",
        "description": "Infrastructure, CI/CD, containers, and deployment",
        "prompt": (
            "You are a DevOps engineer expert in:\n"
            "- Docker & Kubernetes orchestration\n"
            "- CI/CD pipelines (GitHub Actions, GitLab CI)\n"
            "- Infrastructure as Code (Terraform, Pulumi)\n"
            "- Monitoring & observability (Prometheus, Grafana)\n"
            "- Cloud platforms (AWS, GCP, Azure)\n"
            "- Security hardening and compliance\n\n"
            "Always consider: cost optimization, scalability, disaster recovery, "
            "and the principle of least privilege."
        ),
        "temperature": 0.4,
        "tags": ["devops", "infrastructure", "cloud"],
    },
    "data_analyst": {
        "name": "Data Analyst",
        "category": "data",
        "description": "Data analysis, SQL, pandas, and visualization",
        "prompt": (
            "You are a data analyst expert in:\n"
            "- SQL query optimization and window functions\n"
            "- Python data analysis (pandas, numpy, polars)\n"
            "- Data visualization (matplotlib, seaborn, plotly)\n"
            "- Statistical analysis and hypothesis testing\n"
            "- Data cleaning and transformation\n\n"
            "Always validate assumptions about data, handle missing values, "
            "and provide interpretation alongside raw results."
        ),
        "temperature": 0.4,
        "tags": ["data", "sql", "analytics"],
    },
    "hindi": {
        "name": "Hindi / Hinglish",
        "category": "language",
        "description": "Respond in Hindi or Hinglish as appropriate",
        "prompt": (
            "Tum ALD-01 ho, Aditya ka AI assistant. "
            "Tum Hindi aur Hinglish mein fluently baat kar sakte ho. "
            "Technical terms ko English mein rakh sakte ho, "
            "baaki conversation Hindi mein karo. "
            "Friendly aur relatable tone rakho, jaise ek dost baat kar raha ho. "
            "Coding examples ke comments Hindi mein likho jab appropriate ho."
        ),
        "temperature": 0.7,
        "tags": ["hindi", "hinglish", "language"],
    },
    "security_expert": {
        "name": "Security Expert",
        "category": "security",
        "description": "Cybersecurity analysis and hardening",
        "prompt": (
            "You are a cybersecurity expert. Analyze everything through a security lens:\n"
            "- OWASP Top 10 vulnerabilities\n"
            "- Authentication and authorization flaws\n"
            "- Input validation and injection prevention\n"
            "- Cryptographic best practices\n"
            "- Network security and zero-trust architecture\n"
            "- Supply chain and dependency risks\n"
            "- Compliance (GDPR, SOC2, HIPAA)\n\n"
            "Always provide severity ratings and remediation steps."
        ),
        "temperature": 0.3,
        "tags": ["security", "vulnerability", "compliance"],
    },
}


# ── User Prompt Templates ──

PROMPT_TEMPLATES = {
    "explain_code": {
        "name": "Explain Code",
        "template": "Explain this code step by step:\n\n```{language}\n{code}\n```",
        "variables": ["language", "code"],
        "category": "coding",
    },
    "fix_error": {
        "name": "Fix Error",
        "template": "I'm getting this error:\n\n```\n{error}\n```\n\nIn this code:\n\n```{language}\n{code}\n```\n\nPlease fix it and explain why it happened.",
        "variables": ["error", "language", "code"],
        "category": "debugging",
    },
    "write_tests": {
        "name": "Write Tests",
        "template": "Write comprehensive unit tests for this code using {framework}:\n\n```{language}\n{code}\n```\n\nInclude edge cases and error scenarios.",
        "variables": ["framework", "language", "code"],
        "category": "testing",
    },
    "optimize": {
        "name": "Optimize Code",
        "template": "Optimize this code for {optimization_goal}:\n\n```{language}\n{code}\n```\n\nExplain the performance improvements.",
        "variables": ["optimization_goal", "language", "code"],
        "category": "performance",
    },
    "convert": {
        "name": "Convert Code",
        "template": "Convert this {source_language} code to {target_language}:\n\n```{source_language}\n{code}\n```\n\nUse idiomatic {target_language} patterns.",
        "variables": ["source_language", "target_language", "code"],
        "category": "conversion",
    },
    "review": {
        "name": "Code Review",
        "template": "Review this code for bugs, security issues, and improvements:\n\n```{language}\n{code}\n```\n\nRate each issue: Critical / Warning / Suggestion.",
        "variables": ["language", "code"],
        "category": "review",
    },
    "document": {
        "name": "Write Documentation",
        "template": "Write comprehensive documentation for:\n\n```{language}\n{code}\n```\n\nInclude: purpose, parameters, return values, examples, and edge cases.",
        "variables": ["language", "code"],
        "category": "documentation",
    },
    "sql_query": {
        "name": "Generate SQL",
        "template": "Write a SQL query that: {description}\n\nSchema:\n```sql\n{schema}\n```\n\nOptimize for {database} and explain the query plan.",
        "variables": ["description", "schema", "database"],
        "category": "data",
    },
    "api_design": {
        "name": "Design API",
        "template": "Design a RESTful API for: {description}\n\nInclude:\n- Endpoints with HTTP methods\n- Request/response schemas\n- Authentication\n- Error handling\n- Rate limiting",
        "variables": ["description"],
        "category": "architecture",
    },
    "refactor": {
        "name": "Refactor Code",
        "template": "Refactor this code following {design_pattern} pattern:\n\n```{language}\n{code}\n```\n\nApply SOLID principles and explain each change.",
        "variables": ["design_pattern", "language", "code"],
        "category": "refactoring",
    },
}


class PromptVersion:
    """Tracks a specific version of a prompt."""

    def __init__(self, prompt: str, version: int, reason: str = ""):
        self.prompt = prompt
        self.version = version
        self.reason = reason
        self.created_at = time.time()
        self.usage_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt[:200] + "..." if len(self.prompt) > 200 else self.prompt,
            "version": self.version,
            "reason": self.reason,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
        }


class PromptLibrary:
    """
    Manages system prompts, user templates, and prompt versioning.

    Features:
    - Built-in curated prompts for different roles
    - User prompt templates with variable substitution
    - Prompt versioning and history
    - Usage tracking and statistics
    - Custom prompt creation and storage
    - Prompt chaining for complex workflows
    """

    def __init__(self):
        self._custom_prompts: Dict[str, Dict[str, Any]] = {}
        self._prompt_history: Dict[str, List[Dict]] = {}
        self._active_prompt: str = "default"
        self._chains: Dict[str, List[str]] = {}
        self._persistence_path = os.path.join(CONFIG_DIR, "prompts.json")
        self._load()

    def get_system_prompt(self, prompt_id: str = "") -> Dict[str, Any]:
        """Get a system prompt by ID."""
        pid = prompt_id or self._active_prompt
        prompt = SYSTEM_PROMPTS.get(pid)
        if prompt:
            return {"id": pid, **prompt, "builtin": True}
        prompt = self._custom_prompts.get(pid)
        if prompt:
            return {"id": pid, **prompt, "builtin": False}
        return {"id": "default", **SYSTEM_PROMPTS["default"], "builtin": True}

    def set_active(self, prompt_id: str) -> bool:
        """Set the active system prompt."""
        if prompt_id in SYSTEM_PROMPTS or prompt_id in self._custom_prompts:
            self._active_prompt = prompt_id
            self._save()
            return True
        return False

    def get_active(self) -> Dict[str, Any]:
        return self.get_system_prompt(self._active_prompt)

    def get_active_text(self) -> str:
        """Get just the active prompt text."""
        prompt = self.get_active()
        return prompt.get("prompt", "")

    def list_system_prompts(self) -> List[Dict[str, Any]]:
        """List all available system prompts."""
        prompts = []
        for pid, pdata in SYSTEM_PROMPTS.items():
            prompts.append({
                "id": pid,
                "name": pdata["name"],
                "category": pdata["category"],
                "description": pdata["description"],
                "temperature": pdata["temperature"],
                "tags": pdata["tags"],
                "active": pid == self._active_prompt,
                "builtin": True,
            })
        for pid, pdata in self._custom_prompts.items():
            prompts.append({
                "id": pid,
                "name": pdata.get("name", pid),
                "category": pdata.get("category", "custom"),
                "description": pdata.get("description", ""),
                "temperature": pdata.get("temperature", 0.7),
                "tags": pdata.get("tags", []),
                "active": pid == self._active_prompt,
                "builtin": False,
            })
        return prompts

    def add_custom_prompt(
        self, prompt_id: str, name: str, prompt: str,
        description: str = "", category: str = "custom",
        temperature: float = 0.7, tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add a custom system prompt."""
        self._custom_prompts[prompt_id] = {
            "name": name,
            "prompt": prompt,
            "description": description,
            "category": category,
            "temperature": temperature,
            "tags": tags or [],
            "created_at": time.time(),
        }
        self._save()
        return {"success": True, "id": prompt_id}

    def remove_custom_prompt(self, prompt_id: str) -> bool:
        if prompt_id in self._custom_prompts:
            del self._custom_prompts[prompt_id]
            if self._active_prompt == prompt_id:
                self._active_prompt = "default"
            self._save()
            return True
        return False

    def render_template(self, template_id: str, variables: Dict[str, str]) -> Dict[str, Any]:
        """Render a prompt template with variables."""
        tmpl = PROMPT_TEMPLATES.get(template_id)
        if not tmpl:
            return {"success": False, "error": f"Template not found: {template_id}"}

        try:
            rendered = tmpl["template"].format(**variables)
            return {
                "success": True,
                "prompt": rendered,
                "template": tmpl["name"],
                "category": tmpl["category"],
            }
        except KeyError as e:
            return {"success": False, "error": f"Missing variable: {e}"}

    def list_templates(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": tid,
                "name": tdata["name"],
                "category": tdata["category"],
                "variables": tdata["variables"],
            }
            for tid, tdata in PROMPT_TEMPLATES.items()
        ]

    def create_chain(self, chain_id: str, prompt_ids: List[str]) -> Dict[str, Any]:
        """Create a prompt chain — sequence of prompts for multi-step workflows."""
        self._chains[chain_id] = prompt_ids
        self._save()
        return {"success": True, "chain_id": chain_id, "steps": len(prompt_ids)}

    def get_chain(self, chain_id: str) -> List[Dict[str, Any]]:
        steps = self._chains.get(chain_id, [])
        return [self.get_system_prompt(pid) for pid in steps]

    def list_chains(self) -> Dict[str, List[str]]:
        return dict(self._chains)

    def search_prompts(self, query: str) -> List[Dict[str, Any]]:
        """Search prompts by keyword."""
        query_lower = query.lower()
        results = []
        for pid, pdata in {**SYSTEM_PROMPTS, **self._custom_prompts}.items():
            name = pdata.get("name", "").lower()
            desc = pdata.get("description", "").lower()
            tags = [t.lower() for t in pdata.get("tags", [])]
            if (query_lower in name or query_lower in desc
                    or any(query_lower in t for t in tags)):
                results.append({"id": pid, "name": pdata["name"], "category": pdata.get("category", "")})
        return results

    def get_stats(self) -> Dict[str, Any]:
        builtin_count = len(SYSTEM_PROMPTS)
        custom_count = len(self._custom_prompts)
        categories = set()
        for p in {**SYSTEM_PROMPTS, **self._custom_prompts}.values():
            categories.add(p.get("category", ""))
        return {
            "builtin_prompts": builtin_count,
            "custom_prompts": custom_count,
            "total_prompts": builtin_count + custom_count,
            "templates": len(PROMPT_TEMPLATES),
            "chains": len(self._chains),
            "categories": sorted(categories),
            "active_prompt": self._active_prompt,
        }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            data = {
                "active": self._active_prompt,
                "custom": self._custom_prompts,
                "chains": self._chains,
            }
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Prompt library save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._active_prompt = data.get("active", "default")
                self._custom_prompts = data.get("custom", {})
                self._chains = data.get("chains", {})
        except Exception:
            pass


_prompt_lib: Optional[PromptLibrary] = None


def get_prompt_library() -> PromptLibrary:
    global _prompt_lib
    if _prompt_lib is None:
        _prompt_lib = PromptLibrary()
    return _prompt_lib
