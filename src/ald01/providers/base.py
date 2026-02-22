"""
ALD-01 Base Provider
Abstract base for all LLM providers. Every provider talks OpenAI-compatible HTTP.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("ald01.providers")


@dataclass
class ProviderStatus:
    """Status of a provider connection."""
    name: str
    online: bool = False
    latency_ms: float = 0.0
    last_check: float = 0.0
    error: str = ""
    models: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "online": self.online,
            "latency_ms": round(self.latency_ms, 1),
            "last_check": self.last_check,
            "error": self.error,
            "models": self.models,
            "metadata": self.metadata,
        }


@dataclass
class CompletionRequest:
    """Unified completion request."""
    messages: List[Dict[str, str]]
    model: str = "auto"
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    system_prompt: Optional[str] = None
    stop: Optional[List[str]] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    def to_api_body(self, model_override: Optional[str] = None) -> Dict[str, Any]:
        """Convert to OpenAI-compatible API request body."""
        msgs = list(self.messages)
        if self.system_prompt:
            msgs.insert(0, {"role": "system", "content": self.system_prompt})

        body: Dict[str, Any] = {
            "model": model_override or self.model,
            "messages": msgs,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
            "top_p": self.top_p,
        }
        if self.stop:
            body["stop"] = self.stop
        if self.frequency_penalty != 0.0:
            body["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0.0:
            body["presence_penalty"] = self.presence_penalty
        return body


@dataclass
class CompletionResponse:
    """Unified completion response."""
    content: str
    model: str = ""
    provider: str = ""
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "latency_ms": round(self.latency_ms, 1),
        }


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 99)
        self.timeout = config.get("timeout", 60)
        self.default_model = config.get("default_model", "")
        self._status = ProviderStatus(name=name)

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request and return the response."""
        ...

    @abstractmethod
    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream a completion response chunk by chunk."""
        ...

    @abstractmethod
    async def test_connection(self) -> ProviderStatus:
        """Test the provider connection and return status."""
        ...

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models from this provider."""
        ...

    @property
    def status(self) -> ProviderStatus:
        return self._status

    def get_model(self, requested: str = "auto") -> str:
        """Resolve the model name. 'auto' uses default_model."""
        if requested == "auto" or not requested:
            return self.default_model
        return requested

    def __repr__(self) -> str:
        status = "●" if self._status.online else "○"
        return f"{status} {self.name} ({self.default_model})"
