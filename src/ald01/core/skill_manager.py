"""
ALD-01 Skill Manager
Self-installs, learns, and manages skills.
Skills are modular capability packages that ALD can discover and install.
"""

import os
import json
import time
import shutil
import logging
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR, DATA_DIR

logger = logging.getLogger("ald01.skills")


BUILTIN_SKILLS = {
    "python_expert": {
        "name": "Python Expert",
        "icon": "code",
        "description": "Advanced Python development including async, typing, testing, and optimization",
        "category": "programming",
        "level": "advanced",
        "keywords": ["python", "async", "typing", "pytest", "pip", "venv"],
        "system_prompt_addon": (
            "You have advanced Python expertise. Use modern Python 3.12+ features, "
            "type hints, async/await, dataclasses, match statements, and f-strings. "
            "Follow PEP 8 and write clean, documented, testable code."
        ),
    },
    "javascript_fullstack": {
        "name": "JavaScript Full-Stack",
        "icon": "file-code",
        "description": "Modern JavaScript/TypeScript with React, Node.js, and full-stack patterns",
        "category": "programming",
        "level": "advanced",
        "keywords": ["javascript", "typescript", "react", "node", "next.js", "express"],
        "system_prompt_addon": (
            "You have full-stack JavaScript/TypeScript expertise. Use ESM modules, "
            "modern React patterns (hooks, Server Components), Next.js 14+, "
            "and TypeScript strict mode. Follow Airbnb style guide."
        ),
    },
    "devops_master": {
        "name": "DevOps Master",
        "icon": "settings",
        "description": "Docker, Kubernetes, CI/CD, Terraform, and infrastructure automation",
        "category": "infrastructure",
        "level": "advanced",
        "keywords": ["docker", "kubernetes", "terraform", "ci/cd", "github actions", "helm"],
        "system_prompt_addon": (
            "You have DevOps expertise. Implement infrastructure as code with Terraform, "
            "containerize with Docker, orchestrate with Kubernetes, and automate CI/CD. "
            "Follow GitOps practices and security best practices."
        ),
    },
    "security_analyst": {
        "name": "Security Analyst",
        "icon": "shield",
        "description": "Application security, vulnerability scanning, threat modeling, OWASP Top 10",
        "category": "security",
        "level": "advanced",
        "keywords": ["security", "vulnerability", "owasp", "penetration", "encryption", "auth"],
        "system_prompt_addon": (
            "You have cybersecurity expertise. Analyze code for OWASP Top 10 vulnerabilities, "
            "implement secure authentication (JWT, OAuth2), validate inputs, "
            "and follow zero-trust architecture principles."
        ),
    },
    "database_architect": {
        "name": "Database Architect",
        "icon": "database",
        "description": "SQL/NoSQL design, query optimization, migrations, and data modeling",
        "category": "data",
        "level": "advanced",
        "keywords": ["database", "sql", "postgresql", "mongodb", "redis", "migration"],
        "system_prompt_addon": (
            "You have database architecture expertise. Design normalized schemas, "
            "optimize queries with proper indexing, implement connection pooling, "
            "manage migrations, and use appropriate database engines for use cases."
        ),
    },
    "ml_engineer": {
        "name": "ML Engineer",
        "icon": "brain",
        "description": "Machine learning, deep learning, NLP, computer vision, and model deployment",
        "category": "ai",
        "level": "expert",
        "keywords": ["machine learning", "deep learning", "pytorch", "tensorflow", "nlp", "vision"],
        "system_prompt_addon": (
            "You have ML engineering expertise. Build and train models with PyTorch/TensorFlow, "
            "implement NLP and computer vision pipelines, optimize inference, "
            "and deploy models with FastAPI or TensorFlow Serving."
        ),
    },
    "api_designer": {
        "name": "API Designer",
        "icon": "plug",
        "description": "REST, GraphQL, gRPC API design with OpenAPI documentation",
        "category": "architecture",
        "level": "advanced",
        "keywords": ["api", "rest", "graphql", "grpc", "openapi", "swagger"],
        "system_prompt_addon": (
            "You have API design expertise. Design RESTful APIs following best practices, "
            "implement GraphQL schemas, document with OpenAPI 3.1, "
            "and handle versioning, pagination, and error responses properly."
        ),
    },
    "cloud_architect": {
        "name": "Cloud Architect",
        "icon": "cloud",
        "description": "AWS, Azure, GCP architecture and cloud-native patterns",
        "category": "infrastructure",
        "level": "expert",
        "keywords": ["aws", "azure", "gcp", "cloud", "serverless", "lambda"],
        "system_prompt_addon": (
            "You have cloud architecture expertise across AWS, Azure, and GCP. "
            "Design cost-effective, scalable cloud solutions using serverless, "
            "microservices, and managed services. Follow Well-Architected Framework."
        ),
    },
    "technical_writer": {
        "name": "Technical Writer",
        "icon": "pen-tool",
        "description": "Documentation, README, API docs, tutorials, and technical blogging",
        "category": "documentation",
        "level": "intermediate",
        "keywords": ["documentation", "readme", "tutorial", "blog", "markdown"],
        "system_prompt_addon": (
            "You have technical writing expertise. Write clear, concise documentation "
            "with proper structure, code examples, and diagrams. "
            "Follow Diátaxis framework for documentation types."
        ),
    },
    "system_admin": {
        "name": "System Admin",
        "icon": "monitor",
        "description": "Linux administration, networking, monitoring, and automation",
        "category": "infrastructure",
        "level": "advanced",
        "keywords": ["linux", "systemd", "nginx", "monitoring", "networking", "bash"],
        "system_prompt_addon": (
            "You have Linux system administration expertise. Configure servers, "
            "manage services with systemd, set up Nginx reverse proxies, "
            "implement monitoring with Prometheus/Grafana, and automate with scripts."
        ),
    },
    "mobile_developer": {
        "name": "Mobile Developer",
        "icon": "smartphone",
        "description": "Flutter, React Native, iOS (Swift), and Android (Kotlin) development",
        "category": "programming",
        "level": "advanced",
        "keywords": ["flutter", "react native", "swift", "kotlin", "mobile", "ios", "android"],
        "system_prompt_addon": (
            "You have mobile development expertise. Build cross-platform apps with Flutter, "
            "implement native features, handle push notifications, offline storage, "
            "and optimize performance for mobile devices."
        ),
    },
    "data_analyst": {
        "name": "Data Analyst",
        "icon": "bar-chart-2",
        "description": "Data analysis with Python, pandas, SQL, and visualization",
        "category": "data",
        "level": "intermediate",
        "keywords": ["data analysis", "pandas", "numpy", "matplotlib", "visualization"],
        "system_prompt_addon": (
            "You have data analysis expertise. Use pandas, numpy, and matplotlib "
            "to analyze datasets, create visualizations, perform statistical analysis, "
            "and generate actionable insights from data."
        ),
    },
    "hindi_support": {
        "name": "Hindi/Hinglish Support",
        "icon": "languages",
        "description": "Respond in Hindi or Hinglish, understand Indian context and culture",
        "category": "language",
        "level": "intermediate",
        "keywords": ["hindi", "hinglish", "indian", "भारतीय"],
        "system_prompt_addon": (
            "You can communicate fluently in Hindi (Devanagari) and Hinglish. "
            "Understand Indian context, cultural references, and programming terminology "
            "as used in India. Be friendly and relatable to Indian developers."
        ),
    },
    "code_reviewer": {
        "name": "Code Reviewer",
        "icon": "search",
        "description": "In-depth code review with security, performance, and style analysis",
        "category": "quality",
        "level": "advanced",
        "keywords": ["code review", "lint", "quality", "refactor", "clean code"],
        "system_prompt_addon": (
            "You have code review expertise. Analyze code for bugs, security issues, "
            "performance problems, code smells, and adherence to clean code principles. "
            "Provide actionable suggestions with examples."
        ),
    },
    "prompt_engineer": {
        "name": "Prompt Engineer",
        "icon": "message-square",
        "description": "Craft effective prompts for LLMs, optimize AI outputs",
        "category": "ai",
        "level": "intermediate",
        "keywords": ["prompt", "llm", "ai", "chain of thought", "system prompt"],
        "system_prompt_addon": (
            "You have prompt engineering expertise. Craft effective system prompts, "
            "use chain-of-thought reasoning, structured output formats, "
            "and optimize prompts for different LLM models."
        ),
    },
}


class SkillManager:
    """
    Manages ALD-01's skills — installable capability packages.
    
    Skills can be:
    - Built-in (always available)
    - Installed by ALD automatically based on user needs
    - Custom-created by the user
    """

    def __init__(self):
        self._installed_skills: Dict[str, Dict[str, Any]] = {}
        self._persistence_path = os.path.join(CONFIG_DIR, "skills.json")
        self._custom_skills_dir = os.path.join(DATA_DIR, "important", "skills")
        os.makedirs(self._custom_skills_dir, exist_ok=True)
        self._load()

    def install_skill(self, skill_id: str) -> Dict[str, Any]:
        """Install a skill from the built-in catalog."""
        if skill_id in BUILTIN_SKILLS:
            skill_data = BUILTIN_SKILLS[skill_id].copy()
            skill_data["installed_at"] = time.time()
            skill_data["enabled"] = True
            self._installed_skills[skill_id] = skill_data
            self._save()

            # Activate brain node
            try:
                from ald01.core.brain import get_brain
                brain = get_brain()
                node_id = f"skill_installed_{skill_id}"
                brain.learn_topic(skill_data["name"], 0.2)
            except Exception:
                pass

            return {"success": True, "skill": skill_data}
        return {"success": False, "error": f"Skill not found: {skill_id}"}

    def uninstall_skill(self, skill_id: str) -> bool:
        if skill_id in self._installed_skills:
            del self._installed_skills[skill_id]
            self._save()
            return True
        return False

    def enable_skill(self, skill_id: str) -> bool:
        if skill_id in self._installed_skills:
            self._installed_skills[skill_id]["enabled"] = True
            self._save()
            return True
        return False

    def disable_skill(self, skill_id: str) -> bool:
        if skill_id in self._installed_skills:
            self._installed_skills[skill_id]["enabled"] = False
            self._save()
            return True
        return False

    def list_available(self) -> List[Dict[str, Any]]:
        """List all available skills (catalog)."""
        return [
            {
                "id": sid,
                **sdata,
                "installed": sid in self._installed_skills,
                "enabled": self._installed_skills.get(sid, {}).get("enabled", False),
            }
            for sid, sdata in BUILTIN_SKILLS.items()
        ]

    def list_installed(self) -> List[Dict[str, Any]]:
        """List installed skills."""
        return [
            {"id": sid, **sdata}
            for sid, sdata in self._installed_skills.items()
        ]

    def get_active_prompt_addons(self) -> str:
        """Get all active skill prompt additions."""
        addons = []
        for sid, sdata in self._installed_skills.items():
            if sdata.get("enabled") and sdata.get("system_prompt_addon"):
                addons.append(sdata["system_prompt_addon"])
        return "\n\n".join(addons)

    def auto_recommend(self, query: str) -> List[str]:
        """Recommend skills to install based on a query."""
        query_lower = query.lower()
        recommendations = []
        for sid, sdata in BUILTIN_SKILLS.items():
            if sid in self._installed_skills:
                continue
            keywords = sdata.get("keywords", [])
            if any(kw in query_lower for kw in keywords):
                recommendations.append(sid)
        return recommendations[:5]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_available": len(BUILTIN_SKILLS),
            "installed": len(self._installed_skills),
            "enabled": sum(1 for s in self._installed_skills.values() if s.get("enabled")),
            "categories": list(set(s.get("category", "") for s in BUILTIN_SKILLS.values())),
        }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(self._installed_skills, f, indent=2)
        except Exception as e:
            logger.warning(f"Skill save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, encoding="utf-8") as f:
                    self._installed_skills = json.load(f)
        except Exception:
            self._installed_skills = {}


_skill_mgr: Optional[SkillManager] = None

def get_skill_manager() -> SkillManager:
    global _skill_mgr
    if _skill_mgr is None:
        _skill_mgr = SkillManager()
    return _skill_mgr
