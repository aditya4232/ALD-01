"""
ALD-01 Template Engine
Generates code, documents, and project scaffolds from templates.
Supports variable substitution, conditional blocks, loops, and includes.
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ald01 import DATA_DIR

logger = logging.getLogger("ald01.templates")


class TemplateParser:
    """
    Simple but capable template parser.

    Syntax:
      {{ variable }}         - Variable substitution
      {% if condition %}     - Conditional block
      {% endif %}
      {% for item in list %} - Loop
      {% endfor %}
      {# comment #}          - Comment (removed from output)
      {% include "file" %}   - Include another template
    """

    VAR_PATTERN = re.compile(r"\{\{\s*(.+?)\s*\}\}")
    BLOCK_PATTERN = re.compile(r"\{%\s*(.+?)\s*%\}")
    COMMENT_PATTERN = re.compile(r"\{#.*?#\}", re.DOTALL)

    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template string with the given context."""
        # Remove comments
        output = self.COMMENT_PATTERN.sub("", template)

        # Process blocks (if/for)
        output = self._process_blocks(output, context)

        # Substitute variables
        output = self._substitute_vars(output, context)

        return output

    def _substitute_vars(self, text: str, context: Dict[str, Any]) -> str:
        def replacer(match):
            expr = match.group(1).strip()
            # Support dot notation: user.name
            value = self._resolve(expr, context)
            if value is None:
                return f"{{{{ {expr} }}}}"
            return str(value)

        return self.VAR_PATTERN.sub(replacer, text)

    def _resolve(self, expr: str, context: Dict[str, Any]) -> Any:
        """Resolve a dotted path like 'user.name' in context."""
        parts = expr.split(".")
        obj = context
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
            if obj is None:
                return None
        return obj

    def _process_blocks(self, text: str, context: Dict[str, Any]) -> str:
        """Process {% if %} and {% for %} blocks."""
        lines = text.split("\n")
        output_lines: List[str] = []
        stack: List[Dict[str, Any]] = []
        skip_depth = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            block_match = self.BLOCK_PATTERN.search(stripped)
            if block_match:
                directive = block_match.group(1).strip()

                # {% if condition %}
                if directive.startswith("if "):
                    condition = directive[3:].strip()
                    if skip_depth > 0:
                        skip_depth += 1
                    else:
                        result = self._eval_condition(condition, context)
                        stack.append({"type": "if", "active": result})
                        if not result:
                            skip_depth = 1

                # {% else %}
                elif directive == "else":
                    if skip_depth <= 1 and stack and stack[-1]["type"] == "if":
                        if stack[-1]["active"]:
                            skip_depth = 1
                        else:
                            skip_depth = 0

                # {% endif %}
                elif directive == "endif":
                    if skip_depth > 0:
                        skip_depth -= 1
                    if stack:
                        stack.pop()

                # {% for item in list %}
                elif directive.startswith("for "):
                    if skip_depth > 0:
                        skip_depth += 1
                        i += 1
                        continue

                    match = re.match(r"for\s+(\w+)\s+in\s+(.+)", directive)
                    if match:
                        var_name = match.group(1)
                        list_expr = match.group(2).strip()
                        iterable = self._resolve(list_expr, context)

                        # Collect loop body
                        loop_body: List[str] = []
                        depth = 1
                        i += 1
                        while i < len(lines) and depth > 0:
                            inner = lines[i].strip()
                            inner_match = self.BLOCK_PATTERN.search(inner)
                            if inner_match:
                                inner_dir = inner_match.group(1).strip()
                                if inner_dir.startswith("for "):
                                    depth += 1
                                elif inner_dir == "endfor":
                                    depth -= 1
                                    if depth == 0:
                                        break
                            loop_body.append(lines[i])
                            i += 1

                        # Execute loop
                        if iterable:
                            for idx, item in enumerate(iterable):
                                loop_ctx = {**context, var_name: item, "loop_index": idx}
                                rendered = self._process_blocks("\n".join(loop_body), loop_ctx)
                                rendered = self._substitute_vars(rendered, loop_ctx)
                                output_lines.append(rendered)

                        i += 1
                        continue

                # {% endfor %}
                elif directive == "endfor":
                    if skip_depth > 0:
                        skip_depth -= 1

                # {% include "path" %}
                elif directive.startswith("include "):
                    if skip_depth == 0:
                        path = directive[8:].strip().strip("\"'")
                        included = self._load_include(path)
                        if included:
                            rendered = self.render(included, context)
                            output_lines.append(rendered)

                else:
                    if skip_depth == 0:
                        output_lines.append(line)

            else:
                if skip_depth == 0:
                    output_lines.append(line)

            i += 1

        return "\n".join(output_lines)

    def _eval_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a simple condition expression."""
        condition = condition.strip()

        # Handle 'not' prefix
        if condition.startswith("not "):
            return not self._eval_condition(condition[4:], context)

        # Handle comparisons
        for op, func in [("==", lambda a, b: a == b), ("!=", lambda a, b: a != b),
                         (">=", lambda a, b: a >= b), ("<=", lambda a, b: a <= b),
                         (">", lambda a, b: a > b), ("<", lambda a, b: a < b)]:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._resolve(left.strip(), context)
                right_val = right.strip().strip("\"'")
                try:
                    right_val = type(left_val)(right_val) if left_val is not None else right_val
                except (ValueError, TypeError):
                    pass
                return func(left_val, right_val)

        # Simple truthiness check
        value = self._resolve(condition, context)
        return bool(value)

    @staticmethod
    def _load_include(path: str) -> Optional[str]:
        templates_dir = os.path.join(DATA_DIR, "important", "templates")
        full_path = os.path.join(templates_dir, path)
        if os.path.exists(full_path):
            with open(full_path, encoding="utf-8") as f:
                return f.read()
        return None


# ──── Built-in Templates ────

BUILTIN_TEMPLATES = {
    "python_module": {
        "name": "Python Module",
        "description": "Standard Python module with docstring, imports, logging, and main block",
        "category": "python",
        "template": '''"""
{{ module_name }}
{{ description }}
"""

import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("{{ logger_name }}")

{% for cls in classes %}
class {{ cls.name }}:
    """{{ cls.description }}"""

    def __init__(self):
        pass

{% endfor %}
{% if has_main %}
def main():
    """Entry point."""
    pass


if __name__ == "__main__":
    main()
{% endif %}
''',
    },
    "fastapi_endpoint": {
        "name": "FastAPI Endpoint",
        "description": "REST API endpoint with request validation and error handling",
        "category": "python",
        "template": '''"""{{ endpoint_name }} API endpoint."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict

router = APIRouter(prefix="/api/{{ prefix }}", tags=["{{ tag }}"])


@router.get("/{{ path }}")
async def get_{{ function_name }}():
    """{{ description }}"""
    try:
        return {"data": [], "success": True}
    except Exception as e:
        raise HTTPException(500, str(e))


{% if has_post %}
@router.post("/{{ path }}")
async def create_{{ function_name }}(request: Request):
    body = await request.json()
    try:
        return {"success": True, "data": body}
    except Exception as e:
        raise HTTPException(400, str(e))
{% endif %}
''',
    },
    "react_component": {
        "name": "React Component",
        "description": "Modern React functional component with TypeScript",
        "category": "javascript",
        "template": '''import React{% if has_state %}, { useState }{% endif %} from 'react';

interface {{ name }}Props {
{% for prop in props %}
  {{ prop.name }}: {{ prop.type }};
{% endfor %}
}

export const {{ name }}: React.FC<{{ name }}Props> = ({ {% for prop in props %}{{ prop.name }}{% endfor %} }) => {
{% if has_state %}
  const [loading, setLoading] = useState(false);
{% endif %}

  return (
    <div className="{{ css_class }}">
      <h2>{{ title }}</h2>
    </div>
  );
};

export default {{ name }};
''',
    },
    "dockerfile": {
        "name": "Dockerfile",
        "description": "Multi-stage Docker build for {{ language }} application",
        "category": "devops",
        "template": '''# ── Build stage ──
FROM {{ base_image }} AS builder
WORKDIR /app
COPY . .
{% if language == "python" %}
RUN pip install --no-cache-dir -r requirements.txt
{% endif %}
{% if language == "node" %}
RUN npm ci --production
{% endif %}

# ── Runtime stage ──
FROM {{ runtime_image }}
WORKDIR /app
COPY --from=builder /app .
{% if port %}
EXPOSE {{ port }}
{% endif %}
CMD {{ cmd }}
''',
    },
    "github_actions": {
        "name": "GitHub Actions CI",
        "description": "CI/CD pipeline with test, lint, and deploy steps",
        "category": "devops",
        "template": '''name: {{ workflow_name }}

on:
  push:
    branches: [{{ branch }}]
  pull_request:
    branches: [{{ branch }}]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
{% if language == "python" %}
      - uses: actions/setup-python@v5
        with:
          python-version: "{{ python_version }}"
      - run: pip install -r requirements.txt
      - run: pytest
{% endif %}
{% if language == "node" %}
      - uses: actions/setup-node@v4
        with:
          node-version: "{{ node_version }}"
      - run: npm ci
      - run: npm test
{% endif %}
''',
    },
    "readme": {
        "name": "README.md",
        "description": "Professional README template with badges and sections",
        "category": "docs",
        "template": '''# {{ project_name }}

{{ description }}

## Features

{% for feature in features %}
- {{ feature }}
{% endfor %}

## Quick Start

```bash
{{ install_command }}
```

## Usage

```{{ language }}
{{ usage_example }}
```

{% if has_api %}
## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
{% for endpoint in endpoints %}
| `{{ endpoint.path }}` | {{ endpoint.method }} | {{ endpoint.description }} |
{% endfor %}
{% endif %}

## License

{{ license }}
''',
    },
}


class TemplateEngine:
    """
    Template engine for ALD-01.
    Generates code, docs, and configs from built-in and custom templates.
    """

    def __init__(self):
        self._parser = TemplateParser()
        self._custom_templates: Dict[str, Dict[str, Any]] = {}
        self._templates_dir = os.path.join(DATA_DIR, "important", "templates")
        os.makedirs(self._templates_dir, exist_ok=True)
        self._load_custom()

    def render(self, template_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Render a template with the given context."""
        # Check built-in
        tmpl = BUILTIN_TEMPLATES.get(template_id)
        if not tmpl:
            tmpl = self._custom_templates.get(template_id)
        if not tmpl:
            return {"success": False, "error": f"Template not found: {template_id}"}

        try:
            rendered = self._parser.render(tmpl["template"], context)
            return {
                "success": True,
                "output": rendered,
                "template": template_id,
                "name": tmpl["name"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def render_string(self, template_str: str, context: Dict[str, Any]) -> str:
        """Render an arbitrary template string."""
        return self._parser.render(template_str, context)

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        templates = []
        for tid, tdata in BUILTIN_TEMPLATES.items():
            templates.append({
                "id": tid,
                "name": tdata["name"],
                "description": tdata["description"],
                "category": tdata["category"],
                "builtin": True,
            })
        for tid, tdata in self._custom_templates.items():
            templates.append({
                "id": tid,
                "name": tdata.get("name", tid),
                "description": tdata.get("description", ""),
                "category": tdata.get("category", "custom"),
                "builtin": False,
            })
        return templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        tmpl = BUILTIN_TEMPLATES.get(template_id)
        if tmpl:
            return {"id": template_id, **tmpl, "builtin": True}
        tmpl = self._custom_templates.get(template_id)
        if tmpl:
            return {"id": template_id, **tmpl, "builtin": False}
        return None

    def add_template(
        self, template_id: str, name: str, template: str,
        description: str = "", category: str = "custom",
    ) -> Dict[str, Any]:
        """Add a custom template."""
        self._custom_templates[template_id] = {
            "name": name,
            "description": description,
            "category": category,
            "template": template,
            "created_at": time.time(),
        }
        self._save_custom()
        return {"success": True, "id": template_id}

    def remove_template(self, template_id: str) -> bool:
        if template_id in self._custom_templates:
            del self._custom_templates[template_id]
            self._save_custom()
            return True
        return False

    def scaffold_project(self, project_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete project structure."""
        scaffolds = {
            "python": self._scaffold_python,
            "fastapi": self._scaffold_fastapi,
            "node": self._scaffold_node,
        }
        handler = scaffolds.get(project_type)
        if not handler:
            return {"success": False, "error": f"Unknown project type: {project_type}"}
        return handler(context)

    def _scaffold_python(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        name = ctx.get("name", "myproject")
        files = {
            f"{name}/__init__.py": f'"""{ name } package."""\n\n__version__ = "0.1.0"\n',
            f"{name}/main.py": self.render_string(
                BUILTIN_TEMPLATES["python_module"]["template"],
                {"module_name": name, "description": ctx.get("description", ""), "logger_name": name, "classes": [], "has_main": True},
            ),
            "pyproject.toml": f'[project]\nname = "{name}"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n',
            "README.md": self.render_string(
                BUILTIN_TEMPLATES["readme"]["template"],
                {"project_name": name, "description": ctx.get("description", ""), "features": ctx.get("features", []), "install_command": f"pip install {name}", "language": "python", "usage_example": f"import {name}", "has_api": False, "license": "MIT"},
            ),
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\ndist/\n*.egg-info/\n",
        }
        return {"success": True, "files": files, "project_type": "python"}

    def _scaffold_fastapi(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        name = ctx.get("name", "api")
        files = {
            f"{name}/__init__.py": "",
            f"{name}/main.py": 'from fastapi import FastAPI\n\napp = FastAPI(title="{{ name }}")\n\n@app.get("/health")\nasync def health():\n    return {"status": "ok"}\n',
            f"{name}/routes/__init__.py": "",
            "requirements.txt": "fastapi>=0.109.0\nuvicorn[standard]>=0.27.0\npydantic>=2.5.0\n",
            "Dockerfile": self.render_string(
                BUILTIN_TEMPLATES["dockerfile"]["template"],
                {"base_image": "python:3.12-slim", "runtime_image": "python:3.12-slim", "language": "python", "port": "8000", "cmd": '["uvicorn", "' + name + '.main:app", "--host", "0.0.0.0"]'},
            ),
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\n.env\n",
        }
        return {"success": True, "files": files, "project_type": "fastapi"}

    def _scaffold_node(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        name = ctx.get("name", "myapp")
        files = {
            "package.json": json.dumps({"name": name, "version": "0.1.0", "type": "module", "scripts": {"start": "node src/index.js", "dev": "node --watch src/index.js"}, "dependencies": {}}, indent=2),
            "src/index.js": f'console.log("{name} started");\n',
            ".gitignore": "node_modules/\ndist/\n.env\n",
        }
        return {"success": True, "files": files, "project_type": "node"}

    def _save_custom(self) -> None:
        path = os.path.join(self._templates_dir, "custom_templates.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._custom_templates, f, indent=2)
        except Exception as e:
            logger.warning(f"Template save failed: {e}")

    def _load_custom(self) -> None:
        path = os.path.join(self._templates_dir, "custom_templates.json")
        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    self._custom_templates = json.load(f)
        except Exception:
            self._custom_templates = {}


_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
    return _engine
