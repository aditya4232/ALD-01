"""
ALD-01 Export System
Generates PDF, Markdown, HTML, and JSON exports of conversations,
analysis reports, brain state, and project documentation.
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ald01 import DATA_DIR

logger = logging.getLogger("ald01.export")

EXPORT_DIR = os.path.join(DATA_DIR, "temp", "exports")


class MarkdownBuilder:
    """Fluent builder for Markdown documents."""

    def __init__(self):
        self._parts: List[str] = []

    def title(self, text: str) -> "MarkdownBuilder":
        self._parts.append(f"# {text}\n")
        return self

    def h2(self, text: str) -> "MarkdownBuilder":
        self._parts.append(f"\n## {text}\n")
        return self

    def h3(self, text: str) -> "MarkdownBuilder":
        self._parts.append(f"\n### {text}\n")
        return self

    def paragraph(self, text: str) -> "MarkdownBuilder":
        self._parts.append(f"\n{text}\n")
        return self

    def code(self, code: str, lang: str = "") -> "MarkdownBuilder":
        self._parts.append(f"\n```{lang}\n{code}\n```\n")
        return self

    def bullet(self, items: List[str]) -> "MarkdownBuilder":
        self._parts.append("\n" + "\n".join(f"- {item}" for item in items) + "\n")
        return self

    def numbered(self, items: List[str]) -> "MarkdownBuilder":
        self._parts.append(
            "\n" + "\n".join(f"{i+1}. {item}" for i, item in enumerate(items)) + "\n"
        )
        return self

    def table(self, headers: List[str], rows: List[List[str]]) -> "MarkdownBuilder":
        header_row = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join("---" for _ in headers) + " |"
        data_rows = "\n".join("| " + " | ".join(row) + " |" for row in rows)
        self._parts.append(f"\n{header_row}\n{separator}\n{data_rows}\n")
        return self

    def hr(self) -> "MarkdownBuilder":
        self._parts.append("\n---\n")
        return self

    def badge(self, label: str, value: str, color: str = "blue") -> "MarkdownBuilder":
        self._parts.append(f"![{label}](https://img.shields.io/badge/{label}-{value}-{color})\n")
        return self

    def quote(self, text: str) -> "MarkdownBuilder":
        self._parts.append(f"\n> {text}\n")
        return self

    def image(self, alt: str, url: str) -> "MarkdownBuilder":
        self._parts.append(f"\n![{alt}]({url})\n")
        return self

    def newline(self) -> "MarkdownBuilder":
        self._parts.append("\n")
        return self

    def raw(self, text: str) -> "MarkdownBuilder":
        self._parts.append(text)
        return self

    def build(self) -> str:
        return "".join(self._parts)


class HTMLBuilder:
    """Builder for styled HTML documents."""

    STYLE = """
    <style>
        body { font-family: 'Inter', -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: #0a0e17; color: #e2e8f0; line-height: 1.6; }
        h1 { color: #f8fafc; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; }
        h2 { color: #cbd5e1; margin-top: 32px; }
        h3 { color: #94a3b8; }
        pre { background: #1e293b; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; }
        code { font-family: 'JetBrains Mono', monospace; background: #1e293b; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; }
        th, td { padding: 10px 14px; border: 1px solid #1e293b; text-align: left; }
        th { background: #1e293b; font-weight: 600; }
        tr:nth-child(even) { background: rgba(30,41,59,0.3); }
        blockquote { border-left: 3px solid #3b82f6; margin: 16px 0; padding: 8px 16px; color: #94a3b8; }
        .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge-blue { background: rgba(59,130,246,0.2); color: #60a5fa; }
        .badge-green { background: rgba(16,185,129,0.2); color: #34d399; }
        .badge-red { background: rgba(239,68,68,0.2); color: #f87171; }
        .badge-yellow { background: rgba(245,158,11,0.2); color: #fbbf24; }
        .stat { text-align: center; padding: 16px; }
        .stat-value { font-size: 28px; font-weight: 700; color: #3b82f6; }
        .stat-label { font-size: 12px; color: #64748b; margin-top: 4px; }
        .meta { font-size: 12px; color: #64748b; margin-top: 8px; }
        .footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #1e293b; font-size: 12px; color: #475569; }
        hr { border: none; border-top: 1px solid #1e293b; margin: 24px 0; }
        ul, ol { padding-left: 24px; }
        li { margin: 4px 0; }
        a { color: #3b82f6; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
    """

    def __init__(self, title: str):
        self._title = title
        self._parts: List[str] = []

    def add(self, html: str) -> "HTMLBuilder":
        self._parts.append(html)
        return self

    def build(self) -> str:
        body = "\n".join(self._parts)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self._title}</title>
{self.STYLE}
</head>
<body>
{body}
<div class="footer">Generated by ALD-01 &middot; {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</body>
</html>"""


class ExportSystem:
    """
    Generates exports in multiple formats.

    Supports:
    - Conversation export (Markdown, HTML, JSON)
    - Analysis report export
    - Brain state export
    - System status report
    - Project documentation generation
    """

    def __init__(self):
        os.makedirs(EXPORT_DIR, exist_ok=True)

    def export_conversation(
        self, messages: List[Dict[str, Any]], title: str = "Conversation",
        format: str = "markdown",
    ) -> Dict[str, Any]:
        """Export a conversation to a file."""
        if format == "markdown":
            content = self._conversation_to_markdown(messages, title)
            ext = "md"
        elif format == "html":
            content = self._conversation_to_html(messages, title)
            ext = "html"
        elif format == "json":
            content = json.dumps({"title": title, "messages": messages, "exported_at": time.time()}, indent=2)
            ext = "json"
        else:
            return {"success": False, "error": f"Unknown format: {format}"}

        filename = f"chat_{self._safe_filename(title)}_{int(time.time())}.{ext}"
        filepath = os.path.join(EXPORT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "path": filepath,
            "filename": filename,
            "format": format,
            "size_bytes": os.path.getsize(filepath),
        }

    def export_analysis_report(
        self, analysis: Dict[str, Any], format: str = "markdown",
    ) -> Dict[str, Any]:
        """Export a code analysis report."""
        summary = analysis.get("summary", {})
        title = f"Code Analysis — {analysis.get('directory', 'Project')}"

        if format == "markdown":
            md = MarkdownBuilder()
            md.title(title)
            md.paragraph(f"Analyzed on {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            md.h2("Summary")
            md.table(
                ["Metric", "Value"],
                [
                    ["Files", str(summary.get("total_files", 0))],
                    ["Total Lines", str(summary.get("total_lines", 0))],
                    ["Code Lines", str(summary.get("code_lines", 0))],
                    ["Functions", str(summary.get("total_functions", 0))],
                    ["Classes", str(summary.get("total_classes", 0))],
                    ["Quality Score", f"{summary.get('quality_score', 0)}/100"],
                    ["Issues", str(summary.get("issues_count", 0))],
                ],
            )

            # Complexity
            dist = analysis.get("complexity_distribution", {})
            md.h2("Complexity Distribution")
            md.table(
                ["Level", "Count"],
                [
                    ["Low (1-5)", str(dist.get("low", 0))],
                    ["Medium (6-10)", str(dist.get("medium", 0))],
                    ["High (11-20)", str(dist.get("high", 0))],
                    ["Very High (20+)", str(dist.get("very_high", 0))],
                ],
            )

            # Hotspots
            hotspots = analysis.get("hotspots", [])
            if hotspots:
                md.h2("Complexity Hotspots")
                md.table(
                    ["Function", "Complexity", "Lines", "File"],
                    [
                        [h["qualified_name"], str(h["complexity"]), str(h["line_count"]), Path(h["module"]).name]
                        for h in hotspots
                    ],
                )

            # Issues
            issues = analysis.get("all_issues", [])
            if issues:
                md.h2(f"Issues ({len(issues)})")
                for issue in issues[:20]:
                    severity = issue.get("severity", "info")
                    md.paragraph(f"**[{severity.upper()}]** {issue.get('message', '')} — Line {issue.get('line', '?')}")

            content = md.build()
            ext = "md"
        elif format == "html":
            content = self._analysis_to_html(analysis, title)
            ext = "html"
        else:
            content = json.dumps(analysis, indent=2, default=str)
            ext = "json"

        filename = f"analysis_{int(time.time())}.{ext}"
        filepath = os.path.join(EXPORT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "path": filepath,
            "filename": filename,
            "format": format,
            "size_bytes": os.path.getsize(filepath),
        }

    def export_brain_state(self, brain_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export brain visualization data."""
        md = MarkdownBuilder()
        md.title("ALD-01 Brain State")
        stats = brain_data.get("stats", {})

        md.h2("Statistics")
        md.table(
            ["Metric", "Value"],
            [
                ["Neural Nodes", str(stats.get("total_nodes", 0))],
                ["Connections", str(stats.get("total_connections", 0))],
                ["Skills", str(stats.get("skills_count", 0))],
                ["Growth Rate", f"{stats.get('growth_rate', 0)}%"],
                ["Strongest", stats.get("strongest_category", "N/A")],
            ],
        )

        nodes = brain_data.get("nodes", [])
        if nodes:
            md.h2("Knowledge Nodes")
            by_category = {}
            for n in nodes:
                cat = n.get("category", "other")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(n)

            for cat, cat_nodes in sorted(by_category.items()):
                md.h3(cat.capitalize())
                md.table(
                    ["Node", "Strength", "Connections"],
                    [
                        [n.get("label", n.get("id")), f"{int(n.get('strength', 0) * 100)}%", str(n.get("connections", 0))]
                        for n in sorted(cat_nodes, key=lambda x: x.get("strength", 0), reverse=True)
                    ],
                )

        content = md.build()
        filename = f"brain_state_{int(time.time())}.md"
        filepath = os.path.join(EXPORT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Also export raw JSON
        json_path = filepath.replace(".md", ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(brain_data, f, indent=2, default=str)

        return {
            "success": True,
            "markdown_path": filepath,
            "json_path": json_path,
        }

    def export_status_report(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export system status as a report."""
        md = MarkdownBuilder()
        md.title("ALD-01 System Status Report")
        md.paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        md.h2("System Health")
        md.bullet([
            f"Uptime: {status_data.get('uptime_human', 'unknown')}",
            f"Total Requests: {status_data.get('total_requests', 0)}",
            f"Brain Power: {status_data.get('brain_power', 'N/A')}",
        ])

        providers = status_data.get("providers", {})
        if providers:
            md.h2("Provider Status")
            md.table(
                ["Provider", "Status", "Model"],
                [
                    [name, info.get("status", "?"), info.get("model", "?")]
                    for name, info in providers.items()
                    if isinstance(info, dict)
                ],
            )

        memory = status_data.get("memory", {})
        if memory:
            md.h2("Memory")
            md.bullet([
                f"Total Messages: {memory.get('total_messages', 0)}",
                f"Conversations: {memory.get('conversation_count', 0)}",
                f"Storage: {memory.get('storage_mb', 0)} MB",
            ])

        content = md.build()
        filename = f"status_report_{int(time.time())}.md"
        filepath = os.path.join(EXPORT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True, "path": filepath, "filename": filename}

    def list_exports(self) -> List[Dict[str, Any]]:
        """List all exported files."""
        exports = []
        for fname in sorted(os.listdir(EXPORT_DIR), reverse=True):
            fpath = os.path.join(EXPORT_DIR, fname)
            if os.path.isfile(fpath):
                exports.append({
                    "filename": fname,
                    "path": fpath,
                    "size_bytes": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath),
                    "format": Path(fname).suffix[1:],
                })
        return exports[:50]

    def cleanup_old(self, max_age_days: int = 7) -> int:
        """Remove exports older than max_age_days."""
        cutoff = time.time() - max_age_days * 86400
        removed = 0
        for fname in os.listdir(EXPORT_DIR):
            fpath = os.path.join(EXPORT_DIR, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                removed += 1
        return removed

    # ── Internal helpers ──

    def _conversation_to_markdown(self, messages: List[Dict], title: str) -> str:
        md = MarkdownBuilder()
        md.title(title)
        md.paragraph(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        for msg in messages:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            md.h3(f"{role}")
            md.paragraph(content)
            meta_parts = []
            if msg.get("agent"):
                meta_parts.append(f"Agent: {msg['agent']}")
            if msg.get("model"):
                meta_parts.append(f"Model: {msg['model']}")
            if meta_parts:
                md.paragraph(f"*{' · '.join(meta_parts)}*")
            md.hr()

        return md.build()

    def _conversation_to_html(self, messages: List[Dict], title: str) -> str:
        html = HTMLBuilder(title)
        html.add(f"<h1>{self._escape(title)}</h1>")

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            bg = "rgba(59,130,246,0.1)" if role == "assistant" else "rgba(255,255,255,0.03)"
            html.add(f'<div style="background:{bg};padding:16px;border-radius:8px;margin:12px 0">')
            html.add(f'<strong style="color:{"#3b82f6" if role == "assistant" else "#e2e8f0"}">{role.capitalize()}</strong>')
            html.add(f'<div style="margin-top:8px;white-space:pre-wrap">{self._escape(content)}</div>')
            html.add("</div>")

        return html.build()

    def _analysis_to_html(self, analysis: Dict, title: str) -> str:
        summary = analysis.get("summary", {})
        html = HTMLBuilder(title)
        html.add(f"<h1>{self._escape(title)}</h1>")

        # Stats grid
        html.add('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0">')
        for label, value in [
            ("Files", summary.get("total_files", 0)),
            ("Lines", summary.get("total_lines", 0)),
            ("Quality", f"{summary.get('quality_score', 0)}/100"),
            ("Issues", summary.get("issues_count", 0)),
        ]:
            html.add(f'<div class="stat"><div class="stat-value">{value}</div><div class="stat-label">{label}</div></div>')
        html.add("</div>")

        return html.build()

    @staticmethod
    def _safe_filename(name: str) -> str:
        return re.sub(r"[^\w\-]", "_", name)[:40].strip("_")

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


_export: Optional[ExportSystem] = None


def get_export_system() -> ExportSystem:
    global _export
    if _export is None:
        _export = ExportSystem()
    return _export
