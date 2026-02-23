"""
ALD-01 Code Analyzer
Static analysis engine for Python codebases.
Provides complexity metrics, dependency graphs, code quality scores,
security checks, and improvement suggestions.
"""

import os
import re
import ast
import json
import time
import logging
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ald01.analyzer")


class FunctionMetrics:
    """Metrics for a single function or method."""

    __slots__ = (
        "name", "module", "class_name", "lineno", "end_lineno",
        "line_count", "param_count", "return_count",
        "complexity", "docstring", "decorators", "is_async",
    )

    def __init__(self, name: str, module: str = ""):
        self.name = name
        self.module = module
        self.class_name = ""
        self.lineno = 0
        self.end_lineno = 0
        self.line_count = 0
        self.param_count = 0
        self.return_count = 0
        self.complexity = 1  # Cyclomatic complexity starts at 1
        self.docstring = False
        self.decorators: List[str] = []
        self.is_async = False

    @property
    def qualified_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "module": self.module,
            "class_name": self.class_name,
            "lineno": self.lineno,
            "line_count": self.line_count,
            "param_count": self.param_count,
            "return_count": self.return_count,
            "complexity": self.complexity,
            "has_docstring": self.docstring,
            "is_async": self.is_async,
            "decorators": self.decorators,
        }


class ModuleMetrics:
    """Metrics for a single Python module."""

    def __init__(self, path: str):
        self.path = path
        self.name = Path(path).stem
        self.line_count = 0
        self.code_lines = 0  # Non-blank, non-comment
        self.blank_lines = 0
        self.comment_lines = 0
        self.docstring_lines = 0
        self.import_count = 0
        self.class_count = 0
        self.function_count = 0
        self.functions: List[FunctionMetrics] = []
        self.classes: List[str] = []
        self.imports: List[str] = []
        self.todos: List[Dict[str, Any]] = []
        self.issues: List[Dict[str, Any]] = []
        self.has_type_hints = False
        self.has_docstring = False
        self.avg_complexity = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "line_count": self.line_count,
            "code_lines": self.code_lines,
            "blank_lines": self.blank_lines,
            "comment_lines": self.comment_lines,
            "import_count": self.import_count,
            "class_count": self.class_count,
            "function_count": self.function_count,
            "functions": [f.to_dict() for f in self.functions],
            "classes": self.classes,
            "imports": self.imports,
            "todos": self.todos,
            "issues": self.issues,
            "has_type_hints": self.has_type_hints,
            "has_docstring": self.has_docstring,
            "avg_complexity": round(self.avg_complexity, 2),
        }


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor that calculates cyclomatic complexity."""

    COMPLEXITY_NODES = (
        ast.If, ast.While, ast.For, ast.ExceptHandler,
        ast.With, ast.BoolOp, ast.IfExp,
    )

    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Each 'and'/'or' adds a path
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.complexity += 1
        self.generic_visit(node)


class SecurityChecker:
    """Basic security pattern checks for Python code."""

    ISSUES = [
        {
            "id": "SEC001",
            "pattern": re.compile(r"eval\s*\("),
            "severity": "high",
            "message": "Use of eval() — potential code injection risk",
        },
        {
            "id": "SEC002",
            "pattern": re.compile(r"exec\s*\("),
            "severity": "high",
            "message": "Use of exec() — potential code injection risk",
        },
        {
            "id": "SEC003",
            "pattern": re.compile(r"subprocess\.call\s*\(.*shell\s*=\s*True"),
            "severity": "high",
            "message": "subprocess with shell=True — command injection risk",
        },
        {
            "id": "SEC004",
            "pattern": re.compile(r"pickle\.loads?\s*\("),
            "severity": "medium",
            "message": "Pickle deserialization — untrusted data risk",
        },
        {
            "id": "SEC005",
            "pattern": re.compile(r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]"),
            "severity": "high",
            "message": "Hardcoded secret detected",
        },
        {
            "id": "SEC006",
            "pattern": re.compile(r"os\.system\s*\("),
            "severity": "medium",
            "message": "os.system() — prefer subprocess for safety",
        },
        {
            "id": "SEC007",
            "pattern": re.compile(r"__import__\s*\("),
            "severity": "medium",
            "message": "Dynamic import with __import__ — potential injection",
        },
        {
            "id": "SEC008",
            "pattern": re.compile(r"assert\s+"),
            "severity": "low",
            "message": "Assert used for validation — removed in optimized mode (-O)",
        },
        {
            "id": "SEC009",
            "pattern": re.compile(r"yaml\.load\s*\([^)]*\)(?!.*Loader)"),
            "severity": "medium",
            "message": "yaml.load without Loader — use safe_load instead",
        },
        {
            "id": "SEC010",
            "pattern": re.compile(r"verify\s*=\s*False"),
            "severity": "high",
            "message": "SSL verification disabled — MitM risk",
        },
    ]

    def check(self, code: str, filepath: str = "") -> List[Dict[str, Any]]:
        issues = []
        for lineno, line in enumerate(code.split("\n"), 1):
            for check in self.ISSUES:
                if check["pattern"].search(line):
                    issues.append({
                        "id": check["id"],
                        "severity": check["severity"],
                        "message": check["message"],
                        "file": filepath,
                        "line": lineno,
                        "code": line.strip()[:100],
                    })
        return issues


class CodeAnalyzer:
    """
    Static analysis engine for Python codebases.

    Features:
    - Cyclomatic complexity per function
    - Line counting (code, blank, comment, docstring)
    - Import dependency mapping
    - Security pattern checking
    - TODO/FIXME extraction
    - Quality scoring (0-100)
    - Improvement suggestions
    """

    def __init__(self):
        self._security_checker = SecurityChecker()
        self._cache: Dict[str, Dict[str, Any]] = {}

    def analyze_file(self, filepath: str) -> ModuleMetrics:
        """Analyze a single Python file."""
        metrics = ModuleMetrics(filepath)

        try:
            with open(filepath, encoding="utf-8") as f:
                code = f.read()
        except (OSError, UnicodeDecodeError) as e:
            metrics.issues.append({"severity": "error", "message": f"Cannot read file: {e}"})
            return metrics

        lines = code.split("\n")
        metrics.line_count = len(lines)

        # Count line types
        in_docstring = False
        docstring_char = None
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track docstrings
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    docstring_char = stripped[:3]
                    if stripped.count(docstring_char) >= 2 and len(stripped) > 3:
                        metrics.docstring_lines += 1
                    else:
                        in_docstring = True
                        metrics.docstring_lines += 1
                    continue
            else:
                metrics.docstring_lines += 1
                if docstring_char and docstring_char in stripped:
                    in_docstring = False
                continue

            if not stripped:
                metrics.blank_lines += 1
            elif stripped.startswith("#"):
                metrics.comment_lines += 1
                # Extract TODOs
                if "TODO" in stripped or "FIXME" in stripped or "HACK" in stripped:
                    metrics.todos.append({"line": lineno, "text": stripped})
            else:
                metrics.code_lines += 1

        # AST analysis
        try:
            tree = ast.parse(code, filename=filepath)
            metrics.has_docstring = bool(ast.get_docstring(tree))
            self._analyze_ast(tree, metrics, filepath)
        except SyntaxError as e:
            metrics.issues.append({
                "severity": "error",
                "message": f"Syntax error at line {e.lineno}: {e.msg}",
                "line": e.lineno,
            })

        # Security checks
        sec_issues = self._security_checker.check(code, filepath)
        metrics.issues.extend(sec_issues)

        # Type hint detection
        metrics.has_type_hints = bool(re.search(r":\s*(str|int|float|bool|List|Dict|Optional|Any|Tuple)", code))

        # Average complexity
        if metrics.functions:
            metrics.avg_complexity = sum(f.complexity for f in metrics.functions) / len(metrics.functions)

        return metrics

    def _analyze_ast(self, tree: ast.AST, metrics: ModuleMetrics, filepath: str) -> None:
        """Extract metrics from AST."""
        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    metrics.imports.append(alias.name)
                    metrics.import_count += 1
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    metrics.imports.append(f"{module}.{alias.name}")
                metrics.import_count += 1

            # Classes
            elif isinstance(node, ast.ClassDef):
                metrics.classes.append(node.name)
                metrics.class_count += 1

                # Analyze methods within the class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        fm = self._analyze_function(item, filepath)
                        fm.class_name = node.name
                        metrics.functions.append(fm)
                        metrics.function_count += 1

            # Top-level functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip methods already counted
                if not any(
                    isinstance(parent, ast.ClassDef)
                    for parent in ast.walk(tree)
                    if hasattr(parent, "body") and node in getattr(parent, "body", [])
                ):
                    fm = self._analyze_function(node, filepath)
                    metrics.functions.append(fm)
                    metrics.function_count += 1

    def _analyze_function(self, node, filepath: str) -> FunctionMetrics:
        fm = FunctionMetrics(node.name, filepath)
        fm.lineno = node.lineno
        fm.end_lineno = getattr(node, "end_lineno", node.lineno)
        fm.line_count = fm.end_lineno - fm.lineno + 1
        fm.is_async = isinstance(node, ast.AsyncFunctionDef)
        fm.docstring = bool(ast.get_docstring(node))
        fm.param_count = len(node.args.args)

        # Decorators
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                fm.decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                fm.decorators.append(f"{getattr(dec.value, 'id', '?')}.{dec.attr}")

        # Cyclomatic complexity
        visitor = ComplexityVisitor()
        visitor.visit(node)
        fm.complexity = visitor.complexity

        # Count returns
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                fm.return_count += 1

        return fm

    def analyze_directory(
        self, directory: str,
        ignore_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Analyze an entire directory of Python files."""
        ignore = set(ignore_patterns or [])
        ignore.update({"__pycache__", ".git", "node_modules", ".venv", "venv"})

        modules: List[ModuleMetrics] = []
        start = time.time()

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ignore]
            for fname in sorted(files):
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                metrics = self.analyze_file(fpath)
                modules.append(metrics)

        elapsed = time.time() - start

        # Aggregate stats
        total_lines = sum(m.line_count for m in modules)
        total_code = sum(m.code_lines for m in modules)
        total_functions = sum(m.function_count for m in modules)
        total_classes = sum(m.class_count for m in modules)
        all_issues = []
        for m in modules:
            all_issues.extend(m.issues)

        # Quality score (0-100)
        quality = self._calculate_quality(modules)

        # Dependency graph
        dep_graph = self._build_dependency_graph(modules)

        # Complexity distribution
        all_complexities = [f.complexity for m in modules for f in m.functions]
        complexity_dist = {
            "low": sum(1 for c in all_complexities if c <= 5),
            "medium": sum(1 for c in all_complexities if 5 < c <= 10),
            "high": sum(1 for c in all_complexities if 10 < c <= 20),
            "very_high": sum(1 for c in all_complexities if c > 20),
        }

        # Find hotspots (high-complexity functions)
        hotspots = sorted(
            [f for m in modules for f in m.functions],
            key=lambda f: f.complexity, reverse=True,
        )[:10]

        return {
            "directory": directory,
            "analysis_time_seconds": round(elapsed, 2),
            "summary": {
                "total_files": len(modules),
                "total_lines": total_lines,
                "code_lines": total_code,
                "total_functions": total_functions,
                "total_classes": total_classes,
                "quality_score": quality,
                "issues_count": len(all_issues),
                "issues_by_severity": {
                    sev: sum(1 for i in all_issues if i.get("severity") == sev)
                    for sev in ("error", "high", "medium", "low")
                },
            },
            "complexity_distribution": complexity_dist,
            "hotspots": [h.to_dict() for h in hotspots],
            "dependency_graph": dep_graph,
            "modules": [m.to_dict() for m in modules],
            "all_issues": all_issues[:100],
        }

    def _calculate_quality(self, modules: List[ModuleMetrics]) -> int:
        """Calculate a quality score from 0-100."""
        if not modules:
            return 0

        score = 100.0
        total_functions = sum(m.function_count for m in modules)
        if total_functions == 0:
            return 50

        # Deductions
        # High complexity functions
        high_complexity = sum(
            1 for m in modules for f in m.functions if f.complexity > 10
        )
        score -= min(20, high_complexity * 2)

        # Missing docstrings
        no_docstring = sum(
            1 for m in modules for f in m.functions if not f.docstring
        )
        docstring_ratio = no_docstring / max(total_functions, 1)
        score -= docstring_ratio * 15

        # Long functions (> 50 lines)
        long_funcs = sum(
            1 for m in modules for f in m.functions if f.line_count > 50
        )
        score -= min(15, long_funcs * 3)

        # Security issues
        sec_issues = sum(len(m.issues) for m in modules)
        score -= min(20, sec_issues * 2)

        # No type hints
        no_types = sum(1 for m in modules if not m.has_type_hints)
        score -= min(10, (no_types / max(len(modules), 1)) * 10)

        # No module docstrings
        no_module_doc = sum(1 for m in modules if not m.has_docstring)
        score -= min(5, (no_module_doc / max(len(modules), 1)) * 5)

        return max(0, min(100, int(score)))

    def _build_dependency_graph(self, modules: List[ModuleMetrics]) -> Dict[str, List[str]]:
        """Build an internal dependency graph."""
        module_names = {m.name for m in modules}
        graph: Dict[str, List[str]] = {}

        for m in modules:
            deps = []
            for imp in m.imports:
                # Check if import refers to another analyzed module
                parts = imp.split(".")
                for part in parts:
                    if part in module_names and part != m.name:
                        deps.append(part)
            graph[m.name] = sorted(set(deps))

        return graph

    def get_suggestions(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate improvement suggestions from analysis results."""
        suggestions = []
        summary = analysis.get("summary", {})

        # High complexity
        hotspots = analysis.get("hotspots", [])
        for h in hotspots[:3]:
            if h["complexity"] > 10:
                suggestions.append({
                    "type": "refactor",
                    "priority": "high",
                    "message": f"Function '{h['qualified_name']}' has complexity {h['complexity']}. Consider breaking it into smaller functions.",
                    "file": h["module"],
                    "line": h["lineno"],
                })

        # Low quality score
        quality = summary.get("quality_score", 100)
        if quality < 60:
            suggestions.append({
                "type": "quality",
                "priority": "high",
                "message": f"Overall quality score is {quality}/100. Focus on docstrings, type hints, and reducing complexity.",
            })

        # Security issues
        issues = analysis.get("all_issues", [])
        high_sec = [i for i in issues if i.get("severity") == "high"]
        if high_sec:
            suggestions.append({
                "type": "security",
                "priority": "critical",
                "message": f"{len(high_sec)} high-severity security issues found. Address these immediately.",
            })

        return suggestions


_analyzer: Optional[CodeAnalyzer] = None


def get_code_analyzer() -> CodeAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = CodeAnalyzer()
    return _analyzer
