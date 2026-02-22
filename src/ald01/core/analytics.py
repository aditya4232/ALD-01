"""
ALD-01 Analytics Engine
Tracks usage metrics, model performance, cost estimation, and generates insights.
All data stays local — no telemetry is sent externally.
"""

import os
import json
import time
import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ald01 import DATA_DIR

logger = logging.getLogger("ald01.analytics")


class MetricPoint:
    """A single metric data point."""

    __slots__ = ("name", "value", "timestamp", "tags")

    def __init__(self, name: str, value: float, timestamp: float = 0, tags: Optional[Dict] = None):
        self.name = name
        self.value = value
        self.timestamp = timestamp or time.time()
        self.tags = tags or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "tags": self.tags,
        }


class TimeSeries:
    """Efficient in-memory time series for a single metric."""

    def __init__(self, name: str, max_points: int = 10_000):
        self.name = name
        self.max_points = max_points
        self._points: List[Tuple[float, float]] = []  # (timestamp, value)

    def add(self, value: float, ts: float = 0) -> None:
        ts = ts or time.time()
        self._points.append((ts, value))
        if len(self._points) > self.max_points:
            # Drop oldest 10%
            cut = self.max_points // 10
            self._points = self._points[cut:]

    def get_range(self, start_ts: float = 0, end_ts: float = 0) -> List[Tuple[float, float]]:
        if not start_ts and not end_ts:
            return self._points[:]
        return [
            (ts, v) for ts, v in self._points
            if (not start_ts or ts >= start_ts) and (not end_ts or ts <= end_ts)
        ]

    def get_stats(self, window_seconds: int = 3600) -> Dict[str, Any]:
        cutoff = time.time() - window_seconds
        recent = [v for ts, v in self._points if ts >= cutoff]
        if not recent:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "sum": 0}
        return {
            "count": len(recent),
            "min": round(min(recent), 4),
            "max": round(max(recent), 4),
            "avg": round(statistics.mean(recent), 4),
            "sum": round(sum(recent), 4),
            "stddev": round(statistics.stdev(recent), 4) if len(recent) > 1 else 0,
        }

    def rate(self, window_seconds: int = 60) -> float:
        """Events per second over the window."""
        cutoff = time.time() - window_seconds
        count = sum(1 for ts, _ in self._points if ts >= cutoff)
        return round(count / max(window_seconds, 1), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_points": len(self._points),
            "stats_1h": self.get_stats(3600),
            "stats_24h": self.get_stats(86400),
            "rate_1m": self.rate(60),
        }


class CostTracker:
    """Estimates API costs based on token usage and model pricing."""

    # Approximate costs per 1K tokens (input / output)
    MODEL_PRICING = {
        "groq": {"input": 0.0, "output": 0.0},  # Free tier
        "cerebras": {"input": 0.0, "output": 0.0},  # Free tier
        "github_copilot": {"input": 0.0, "output": 0.0},
        "openai_gpt4": {"input": 0.03, "output": 0.06},
        "openai_gpt35": {"input": 0.0015, "output": 0.002},
        "anthropic_claude3": {"input": 0.008, "output": 0.024},
        "anthropic_claude35": {"input": 0.003, "output": 0.015},
        "google_gemini": {"input": 0.00035, "output": 0.00105},
        "local_ollama": {"input": 0.0, "output": 0.0},
    }

    def __init__(self):
        self._usage: List[Dict[str, Any]] = []

    def record_usage(
        self, model: str, input_tokens: int, output_tokens: int,
        provider: str = "", latency_ms: float = 0,
    ) -> Dict[str, Any]:
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING.get(provider, {"input": 0, "output": 0}))
        cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

        entry = {
            "timestamp": time.time(),
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost, 6),
            "latency_ms": latency_ms,
        }
        self._usage.append(entry)

        # Keep last 5000 entries
        if len(self._usage) > 5000:
            self._usage = self._usage[-4000:]

        return entry

    def get_summary(self, hours: int = 24) -> Dict[str, Any]:
        cutoff = time.time() - hours * 3600
        recent = [u for u in self._usage if u["timestamp"] >= cutoff]

        if not recent:
            return {
                "period_hours": hours,
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "by_model": {},
                "by_provider": {},
            }

        by_model: Dict[str, Dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0})
        by_provider: Dict[str, Dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0})

        for u in recent:
            m = by_model[u["model"]]
            m["requests"] += 1
            m["tokens"] += u["total_tokens"]
            m["cost"] += u["cost_usd"]

            if u["provider"]:
                p = by_provider[u["provider"]]
                p["requests"] += 1
                p["tokens"] += u["total_tokens"]
                p["cost"] += u["cost_usd"]

        return {
            "period_hours": hours,
            "total_requests": len(recent),
            "total_tokens": sum(u["total_tokens"] for u in recent),
            "total_input_tokens": sum(u["input_tokens"] for u in recent),
            "total_output_tokens": sum(u["output_tokens"] for u in recent),
            "total_cost_usd": round(sum(u["cost_usd"] for u in recent), 4),
            "avg_latency_ms": round(
                statistics.mean(u["latency_ms"] for u in recent if u["latency_ms"] > 0), 1
            ) if any(u["latency_ms"] > 0 for u in recent) else 0,
            "by_model": dict(by_model),
            "by_provider": dict(by_provider),
        }

    def to_list(self) -> List[Dict[str, Any]]:
        return self._usage[-100:]


class SessionTracker:
    """Tracks user session activity."""

    def __init__(self):
        self.session_start = time.time()
        self._events: List[Dict[str, Any]] = []
        self._page_views: Dict[str, int] = defaultdict(int)
        self._feature_usage: Dict[str, int] = defaultdict(int)

    def record_event(self, event_type: str, data: Optional[Dict] = None) -> None:
        self._events.append({
            "type": event_type,
            "timestamp": time.time(),
            "data": data or {},
        })
        if len(self._events) > 5000:
            self._events = self._events[-4000:]

    def record_page_view(self, page: str) -> None:
        self._page_views[page] += 1
        self.record_event("page_view", {"page": page})

    def record_feature_use(self, feature: str) -> None:
        self._feature_usage[feature] += 1
        self.record_event("feature_use", {"feature": feature})

    def get_session_summary(self) -> Dict[str, Any]:
        duration = time.time() - self.session_start
        return {
            "session_start": datetime.fromtimestamp(self.session_start).isoformat(),
            "duration_seconds": round(duration),
            "duration_human": self._format_duration(duration),
            "total_events": len(self._events),
            "page_views": dict(self._page_views),
            "feature_usage": dict(self._feature_usage),
            "top_pages": sorted(self._page_views.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_features": sorted(self._feature_usage.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


class AnalyticsEngine:
    """
    Central analytics hub for ALD-01.
    Aggregates metrics, cost tracking, and session data.
    All data is local — no external telemetry.
    """

    def __init__(self):
        self._metrics: Dict[str, TimeSeries] = {}
        self.cost_tracker = CostTracker()
        self.session_tracker = SessionTracker()
        self._persistence_path = os.path.join(DATA_DIR, "temp", "analytics.json")
        self._load()

    def record(self, metric_name: str, value: float = 1.0, tags: Optional[Dict] = None) -> None:
        """Record a metric value."""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = TimeSeries(metric_name)
        self._metrics[metric_name].add(value)

    def get_metric(self, metric_name: str) -> Dict[str, Any]:
        ts = self._metrics.get(metric_name)
        if ts:
            return ts.to_dict()
        return {"name": metric_name, "total_points": 0}

    def list_metrics(self) -> List[str]:
        return sorted(self._metrics.keys())

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Comprehensive analytics payload for the dashboard."""
        return {
            "session": self.session_tracker.get_session_summary(),
            "costs": self.cost_tracker.get_summary(24),
            "metrics": {
                name: ts.to_dict()
                for name, ts in self._metrics.items()
            },
            "metric_names": self.list_metrics(),
        }

    def record_chat(self, model: str = "", provider: str = "", input_tokens: int = 0,
                     output_tokens: int = 0, latency_ms: float = 0) -> None:
        """Convenience method to record a chat interaction."""
        self.record("chat.requests")
        self.record("chat.input_tokens", input_tokens)
        self.record("chat.output_tokens", output_tokens)
        if latency_ms > 0:
            self.record("chat.latency_ms", latency_ms)
        if model:
            self.record(f"chat.model.{model}")
        self.cost_tracker.record_usage(model, input_tokens, output_tokens, provider, latency_ms)

    def record_api_call(self, endpoint: str, status_code: int = 200, latency_ms: float = 0) -> None:
        self.record("api.requests")
        self.record(f"api.status.{status_code}")
        if latency_ms > 0:
            self.record("api.latency_ms", latency_ms)

    def record_error(self, error_type: str, module: str = "") -> None:
        self.record("errors.total")
        self.record(f"errors.type.{error_type}")
        if module:
            self.record(f"errors.module.{module}")

    def get_health_metrics(self) -> Dict[str, Any]:
        """Health-focused metrics for monitoring."""
        return {
            "requests_1m": self._metrics.get("api.requests", TimeSeries("")).rate(60),
            "errors_1h": self._metrics.get("errors.total", TimeSeries("")).get_stats(3600).get("count", 0),
            "avg_latency_ms": self._metrics.get("api.latency_ms", TimeSeries("")).get_stats(300).get("avg", 0),
            "chat_requests_1h": self._metrics.get("chat.requests", TimeSeries("")).get_stats(3600).get("count", 0),
            "total_tokens_1h": self._metrics.get("chat.input_tokens", TimeSeries("")).get_stats(3600).get("sum", 0)
                + self._metrics.get("chat.output_tokens", TimeSeries("")).get_stats(3600).get("sum", 0),
        }

    def save(self) -> None:
        """Persist analytics snapshot."""
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            data = {
                "saved_at": time.time(),
                "session_start": self.session_tracker.session_start,
                "page_views": dict(self.session_tracker._page_views),
                "feature_usage": dict(self.session_tracker._feature_usage),
                "cost_usage": self.cost_tracker._usage[-500:],
            }
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Analytics save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, encoding="utf-8") as f:
                    data = json.load(f)
                self.cost_tracker._usage = data.get("cost_usage", [])
                for page, count in data.get("page_views", {}).items():
                    self.session_tracker._page_views[page] = count
                for feat, count in data.get("feature_usage", {}).items():
                    self.session_tracker._feature_usage[feat] = count
        except Exception:
            pass


_analytics: Optional[AnalyticsEngine] = None


def get_analytics() -> AnalyticsEngine:
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsEngine()
    return _analytics
