"""
ALD-01 Webhook Engine
Outgoing webhook system for integrating ALD with external services.
Supports event subscriptions, retry logic, HMAC signing, and delivery tracking.
"""

import os
import json
import time
import hmac
import hashlib
import asyncio
import logging
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional
from urllib.parse import urlparse

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.webhooks")


class WebhookDelivery:
    """Record of a single webhook delivery attempt."""

    __slots__ = (
        "webhook_id", "event", "url", "status_code",
        "response_body", "latency_ms", "timestamp",
        "success", "attempt", "error",
    )

    def __init__(self, webhook_id: str, event: str, url: str):
        self.webhook_id = webhook_id
        self.event = event
        self.url = url
        self.status_code: int = 0
        self.response_body: str = ""
        self.latency_ms: float = 0
        self.timestamp: float = time.time()
        self.success: bool = False
        self.attempt: int = 1
        self.error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "event": self.event,
            "url": self.url,
            "status_code": self.status_code,
            "latency_ms": round(self.latency_ms, 1),
            "timestamp": self.timestamp,
            "success": self.success,
            "attempt": self.attempt,
            "error": self.error,
        }


class WebhookSubscription:
    """A registered webhook endpoint."""

    def __init__(
        self, webhook_id: str, url: str, events: List[str],
        secret: str = "", active: bool = True,
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3, timeout: int = 10,
    ):
        self.webhook_id = webhook_id
        self.url = url
        self.events = events
        self.secret = secret
        self.active = active
        self.headers = headers or {}
        self.max_retries = max_retries
        self.timeout = timeout
        self.created_at = time.time()
        self.delivery_count = 0
        self.failure_count = 0
        self.last_delivery: Optional[float] = None

    def matches_event(self, event: str) -> bool:
        """Check if this webhook subscribes to the given event."""
        if "*" in self.events:
            return True
        for pattern in self.events:
            if pattern == event:
                return True
            # Wildcard matching: "chat.*" matches "chat.message"
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event.startswith(prefix):
                    return True
        return False

    def sign_payload(self, payload: bytes) -> str:
        """Generate HMAC-SHA256 signature for the payload."""
        if not self.secret:
            return ""
        return hmac.new(
            self.secret.encode("utf-8"), payload, hashlib.sha256,
        ).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.webhook_id,
            "url": self.url,
            "events": self.events,
            "active": self.active,
            "has_secret": bool(self.secret),
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "created_at": self.created_at,
            "delivery_count": self.delivery_count,
            "failure_count": self.failure_count,
            "last_delivery": self.last_delivery,
            "success_rate": round(
                (self.delivery_count - self.failure_count) / max(self.delivery_count, 1) * 100, 1
            ),
        }


# Supported events
WEBHOOK_EVENTS = [
    "chat.message",
    "chat.response",
    "chat.error",
    "system.startup",
    "system.shutdown",
    "system.health_check",
    "system.error",
    "brain.learn",
    "brain.milestone",
    "skill.installed",
    "skill.uninstalled",
    "task.started",
    "task.completed",
    "task.failed",
    "backup.created",
    "backup.restored",
    "notification.sent",
    "file.changed",
    "schedule.triggered",
    "mode.changed",
    "status.changed",
    "provider.error",
    "provider.switched",
]


class WebhookEngine:
    """
    Manages outgoing webhooks with retry, signing, and delivery tracking.

    Features:
    - Event-based subscriptions with wildcard support
    - HMAC-SHA256 payload signing
    - Automatic retries with exponential backoff
    - Delivery history and success tracking
    - Rate limiting per webhook
    - Async non-blocking delivery
    """

    MAX_DELIVERIES_HISTORY = 500
    RATE_LIMIT_PER_MINUTE = 60

    def __init__(self):
        self._subscriptions: Dict[str, WebhookSubscription] = {}
        self._deliveries: Deque[Dict[str, Any]] = deque(maxlen=self.MAX_DELIVERIES_HISTORY)
        self._rate_counters: Dict[str, List[float]] = {}
        self._persistence_path = os.path.join(CONFIG_DIR, "webhooks.json")
        self._load()

    def register(
        self, url: str, events: List[str], secret: str = "",
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3, timeout: int = 10,
    ) -> Dict[str, Any]:
        """Register a new webhook subscription."""
        # Validate URL
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": "URL must use http or https"}

        # Validate events
        for event in events:
            if event != "*" and not event.endswith(".*"):
                if event not in WEBHOOK_EVENTS:
                    return {"success": False, "error": f"Unknown event: {event}"}

        webhook_id = hashlib.md5(f"{url}:{time.time()}".encode()).hexdigest()[:12]
        sub = WebhookSubscription(
            webhook_id=webhook_id, url=url, events=events,
            secret=secret, headers=headers, max_retries=max_retries,
            timeout=timeout,
        )
        self._subscriptions[webhook_id] = sub
        self._save()

        logger.info(f"Webhook registered: {webhook_id} -> {url} [{', '.join(events)}]")
        return {"success": True, "webhook": sub.to_dict()}

    def unregister(self, webhook_id: str) -> bool:
        if webhook_id in self._subscriptions:
            del self._subscriptions[webhook_id]
            self._save()
            return True
        return False

    def enable(self, webhook_id: str) -> bool:
        sub = self._subscriptions.get(webhook_id)
        if sub:
            sub.active = True
            self._save()
            return True
        return False

    def disable(self, webhook_id: str) -> bool:
        sub = self._subscriptions.get(webhook_id)
        if sub:
            sub.active = False
            self._save()
            return True
        return False

    async def emit(self, event: str, payload: Dict[str, Any]) -> int:
        """
        Emit an event to all matching webhooks.
        Returns the number of webhooks triggered.
        """
        triggered = 0
        for sub in self._subscriptions.values():
            if not sub.active or not sub.matches_event(event):
                continue

            # Rate limiting
            if not self._check_rate_limit(sub.webhook_id):
                logger.warning(f"Webhook {sub.webhook_id} rate limited")
                continue

            # Fire async delivery (non-blocking)
            asyncio.create_task(self._deliver(sub, event, payload))
            triggered += 1

        return triggered

    async def _deliver(
        self, sub: WebhookSubscription, event: str, payload: Dict[str, Any],
    ) -> None:
        """Deliver a webhook with retries."""
        import aiohttp  # Lazy import — only needed when actually delivering

        body = json.dumps({
            "event": event,
            "timestamp": time.time(),
            "payload": payload,
            "webhook_id": sub.webhook_id,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ALD-01/2.0",
            "X-ALD-Event": event,
            "X-ALD-Webhook-ID": sub.webhook_id,
            **sub.headers,
        }

        # Add signature if secret is set
        signature = sub.sign_payload(body)
        if signature:
            headers["X-ALD-Signature"] = f"sha256={signature}"

        for attempt in range(1, sub.max_retries + 1):
            delivery = WebhookDelivery(sub.webhook_id, event, sub.url)
            delivery.attempt = attempt
            start = time.time()

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        sub.url, data=body, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=sub.timeout),
                    ) as resp:
                        delivery.status_code = resp.status
                        delivery.response_body = (await resp.text())[:500]
                        delivery.latency_ms = (time.time() - start) * 1000
                        delivery.success = 200 <= resp.status < 300

                        if delivery.success:
                            sub.delivery_count += 1
                            sub.last_delivery = time.time()
                            self._deliveries.append(delivery.to_dict())
                            return

            except asyncio.TimeoutError:
                delivery.error = f"Timeout after {sub.timeout}s"
            except Exception as e:
                delivery.error = str(e)

            delivery.latency_ms = (time.time() - start) * 1000
            self._deliveries.append(delivery.to_dict())

            # Exponential backoff before retry
            if attempt < sub.max_retries:
                backoff = min(2 ** attempt, 30)
                await asyncio.sleep(backoff)

        # All retries exhausted
        sub.failure_count += 1
        logger.warning(f"Webhook delivery failed after {sub.max_retries} attempts: {sub.webhook_id}")

    def _check_rate_limit(self, webhook_id: str) -> bool:
        now = time.time()
        if webhook_id not in self._rate_counters:
            self._rate_counters[webhook_id] = []

        # Clean old entries
        self._rate_counters[webhook_id] = [
            t for t in self._rate_counters[webhook_id] if now - t < 60
        ]

        if len(self._rate_counters[webhook_id]) >= self.RATE_LIMIT_PER_MINUTE:
            return False

        self._rate_counters[webhook_id].append(now)
        return True

    def list_subscriptions(self) -> List[Dict[str, Any]]:
        return [sub.to_dict() for sub in self._subscriptions.values()]

    def get_deliveries(self, limit: int = 50, webhook_id: str = "") -> List[Dict[str, Any]]:
        deliveries = list(self._deliveries)
        if webhook_id:
            deliveries = [d for d in deliveries if d["webhook_id"] == webhook_id]
        return deliveries[-limit:]

    def get_available_events(self) -> List[str]:
        return WEBHOOK_EVENTS[:]

    def get_stats(self) -> Dict[str, Any]:
        total_deliveries = sum(s.delivery_count for s in self._subscriptions.values())
        total_failures = sum(s.failure_count for s in self._subscriptions.values())
        return {
            "total_subscriptions": len(self._subscriptions),
            "active_subscriptions": sum(1 for s in self._subscriptions.values() if s.active),
            "total_deliveries": total_deliveries,
            "total_failures": total_failures,
            "success_rate": round(
                (total_deliveries - total_failures) / max(total_deliveries, 1) * 100, 1
            ),
            "available_events": len(WEBHOOK_EVENTS),
        }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            data = {}
            for wid, sub in self._subscriptions.items():
                data[wid] = {
                    "url": sub.url,
                    "events": sub.events,
                    "secret": sub.secret,
                    "active": sub.active,
                    "headers": sub.headers,
                    "max_retries": sub.max_retries,
                    "timeout": sub.timeout,
                    "created_at": sub.created_at,
                }
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Webhook config save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, encoding="utf-8") as f:
                    data = json.load(f)
                for wid, wdata in data.items():
                    self._subscriptions[wid] = WebhookSubscription(
                        webhook_id=wid, url=wdata["url"],
                        events=wdata["events"], secret=wdata.get("secret", ""),
                        active=wdata.get("active", True),
                        headers=wdata.get("headers"),
                        max_retries=wdata.get("max_retries", 3),
                        timeout=wdata.get("timeout", 10),
                    )
                    self._subscriptions[wid].created_at = wdata.get("created_at", time.time())
        except Exception:
            self._subscriptions = {}


_webhook_engine: Optional[WebhookEngine] = None


def get_webhook_engine() -> WebhookEngine:
    global _webhook_engine
    if _webhook_engine is None:
        _webhook_engine = WebhookEngine()
    return _webhook_engine
