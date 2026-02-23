"""
ALD-01 Rate Limiter & API Gateway
Token-bucket rate limiting, request middleware, and API key management
for the dashboard and external API consumers.
"""

import os
import time
import json
import hmac
import hashlib
import secrets
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.gateway")


class TokenBucket:
    """
    Token bucket rate limiter.
    Refills tokens at a constant rate up to max capacity.
    Each request consumes one token.
    """

    __slots__ = ("capacity", "rate", "tokens", "last_refill")

    def __init__(self, capacity: int = 60, rate: float = 1.0):
        """
        Args:
            capacity: Maximum tokens (burst capacity)
            rate: Tokens added per second
        """
        self.capacity = capacity
        self.rate = rate
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def available(self) -> float:
        self._refill()
        return self.tokens

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def time_until_available(self) -> float:
        """Seconds until at least 1 token is available."""
        self._refill()
        if self.tokens >= 1:
            return 0
        return (1 - self.tokens) / self.rate


class SlidingWindowCounter:
    """
    Sliding window rate limiter.
    Tracks requests per time window with sub-window precision.
    """

    def __init__(self, window_seconds: int = 60, max_requests: int = 100):
        self.window = window_seconds
        self.max_requests = max_requests
        self._requests: List[float] = []

    def allow(self) -> bool:
        self._cleanup()
        if len(self._requests) >= self.max_requests:
            return False
        self._requests.append(time.time())
        return True

    def current_count(self) -> int:
        self._cleanup()
        return len(self._requests)

    def remaining(self) -> int:
        return max(0, self.max_requests - self.current_count())

    def reset_time(self) -> float:
        """Seconds until the oldest request falls out of the window."""
        self._cleanup()
        if not self._requests:
            return 0
        return max(0, self._requests[0] + self.window - time.time())

    def _cleanup(self) -> None:
        cutoff = time.time() - self.window
        self._requests = [t for t in self._requests if t > cutoff]


class APIKey:
    """Represents an API key for external access."""

    def __init__(
        self, key_id: str, key_hash: str, name: str,
        permissions: Optional[List[str]] = None,
        rate_limit: int = 60, active: bool = True,
    ):
        self.key_id = key_id
        self.key_hash = key_hash
        self.name = name
        self.permissions = permissions or ["read"]
        self.rate_limit = rate_limit
        self.active = active
        self.created_at = time.time()
        self.last_used: Optional[float] = None
        self.request_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.key_id,
            "name": self.name,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
            "active": self.active,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "request_count": self.request_count,
        }


class RateLimitResult:
    """Result of a rate limit check."""

    __slots__ = ("allowed", "remaining", "limit", "reset_seconds", "retry_after")

    def __init__(
        self, allowed: bool, remaining: int = 0,
        limit: int = 0, reset_seconds: float = 0,
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.limit = limit
        self.reset_seconds = reset_seconds
        self.retry_after = 0 if allowed else reset_seconds

    def to_headers(self) -> Dict[str, str]:
        """Generate standard rate limit headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_seconds)),
        }
        if not self.allowed:
            headers["Retry-After"] = str(int(self.retry_after) + 1)
        return headers


# Default rate limit tiers
RATE_TIERS = {
    "free": {"requests_per_minute": 30, "burst": 10},
    "basic": {"requests_per_minute": 60, "burst": 20},
    "premium": {"requests_per_minute": 300, "burst": 50},
    "internal": {"requests_per_minute": 1000, "burst": 100},
}


class APIGateway:
    """
    API gateway with rate limiting, key management, and request tracking.

    Features:
    - Token bucket + sliding window rate limiting
    - API key generation with HMAC verification
    - Permission-based access control
    - Per-endpoint rate limits
    - Request logging and analytics
    - IP-based rate limiting for unauthenticated requests
    """

    def __init__(self):
        self._api_keys: Dict[str, APIKey] = {}
        self._ip_limiters: Dict[str, SlidingWindowCounter] = {}
        self._key_limiters: Dict[str, SlidingWindowCounter] = {}
        self._endpoint_limiters: Dict[str, SlidingWindowCounter] = {}
        self._request_log: List[Dict[str, Any]] = []
        self._persistence_path = os.path.join(CONFIG_DIR, "api_keys.json")
        self._blocked_ips: set = set()
        self._load()

    def generate_api_key(
        self, name: str, permissions: Optional[List[str]] = None,
        rate_limit: int = 60,
    ) -> Dict[str, Any]:
        """Generate a new API key."""
        raw_key = secrets.token_urlsafe(32)
        key_id = secrets.token_hex(6)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = APIKey(
            key_id=key_id, key_hash=key_hash, name=name,
            permissions=permissions or ["read"],
            rate_limit=rate_limit,
        )
        self._api_keys[key_id] = api_key
        self._save()

        logger.info(f"API key generated: {key_id} ({name})")

        return {
            "success": True,
            "key_id": key_id,
            "api_key": f"ald_{key_id}_{raw_key}",  # Only shown once
            "name": name,
            "permissions": api_key.permissions,
            "rate_limit": rate_limit,
        }

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return the APIKey object if valid."""
        if not raw_key.startswith("ald_"):
            return None

        parts = raw_key.split("_", 2)
        if len(parts) != 3:
            return None

        key_id = parts[1]
        secret_part = parts[2]

        api_key = self._api_keys.get(key_id)
        if not api_key or not api_key.active:
            return None

        # Verify hash
        computed = hashlib.sha256(secret_part.encode()).hexdigest()
        if not hmac.compare_digest(computed, api_key.key_hash):
            return None

        api_key.last_used = time.time()
        api_key.request_count += 1
        return api_key

    def check_rate_limit(
        self, identifier: str, limit: int = 60,
        window: int = 60, source: str = "ip",
    ) -> RateLimitResult:
        """Check rate limit for an identifier (IP or API key)."""
        limiter_map = self._ip_limiters if source == "ip" else self._key_limiters

        if identifier not in limiter_map:
            limiter_map[identifier] = SlidingWindowCounter(window, limit)

        limiter = limiter_map[identifier]
        allowed = limiter.allow()

        return RateLimitResult(
            allowed=allowed,
            remaining=limiter.remaining(),
            limit=limit,
            reset_seconds=limiter.reset_time(),
        )

    def check_endpoint_limit(self, endpoint: str, limit: int = 120) -> RateLimitResult:
        """Per-endpoint rate limiting."""
        if endpoint not in self._endpoint_limiters:
            self._endpoint_limiters[endpoint] = SlidingWindowCounter(60, limit)

        limiter = self._endpoint_limiters[endpoint]
        allowed = limiter.allow()
        return RateLimitResult(
            allowed=allowed,
            remaining=limiter.remaining(),
            limit=limit,
            reset_seconds=limiter.reset_time(),
        )

    def check_permission(self, api_key: APIKey, required: str) -> bool:
        """Check if an API key has the required permission."""
        if "admin" in api_key.permissions:
            return True
        return required in api_key.permissions

    def revoke_key(self, key_id: str) -> bool:
        if key_id in self._api_keys:
            self._api_keys[key_id].active = False
            self._save()
            return True
        return False

    def delete_key(self, key_id: str) -> bool:
        if key_id in self._api_keys:
            del self._api_keys[key_id]
            self._save()
            return True
        return False

    def list_keys(self) -> List[Dict[str, Any]]:
        return [k.to_dict() for k in self._api_keys.values()]

    def block_ip(self, ip: str) -> None:
        self._blocked_ips.add(ip)

    def unblock_ip(self, ip: str) -> None:
        self._blocked_ips.discard(ip)

    def is_blocked(self, ip: str) -> bool:
        return ip in self._blocked_ips

    def log_request(
        self, method: str, path: str, status: int,
        ip: str = "", key_id: str = "", latency_ms: float = 0,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "method": method,
            "path": path,
            "status": status,
            "ip": ip,
            "key_id": key_id,
            "latency_ms": round(latency_ms, 1),
        }
        self._request_log.append(entry)
        if len(self._request_log) > 5000:
            self._request_log = self._request_log[-4000:]

    def get_request_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._request_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        recent = [r for r in self._request_log if now - r["timestamp"] < 3600]
        return {
            "total_keys": len(self._api_keys),
            "active_keys": sum(1 for k in self._api_keys.values() if k.active),
            "blocked_ips": len(self._blocked_ips),
            "requests_last_hour": len(recent),
            "avg_latency_ms": round(
                sum(r["latency_ms"] for r in recent) / max(len(recent), 1), 1
            ),
            "status_codes": {
                str(s): sum(1 for r in recent if r["status"] == s)
                for s in set(r["status"] for r in recent)
            } if recent else {},
        }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            data = {}
            for kid, key in self._api_keys.items():
                data[kid] = {
                    "key_hash": key.key_hash,
                    "name": key.name,
                    "permissions": key.permissions,
                    "rate_limit": key.rate_limit,
                    "active": key.active,
                    "created_at": key.created_at,
                }
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"API key save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, encoding="utf-8") as f:
                    data = json.load(f)
                for kid, kdata in data.items():
                    self._api_keys[kid] = APIKey(
                        key_id=kid,
                        key_hash=kdata["key_hash"],
                        name=kdata["name"],
                        permissions=kdata.get("permissions", ["read"]),
                        rate_limit=kdata.get("rate_limit", 60),
                        active=kdata.get("active", True),
                    )
                    self._api_keys[kid].created_at = kdata.get("created_at", time.time())
        except Exception:
            self._api_keys = {}


_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    global _gateway
    if _gateway is None:
        _gateway = APIGateway()
    return _gateway
