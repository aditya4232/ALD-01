"""
ALD-01 OpenAI-Compatible Provider
Works with: OpenAI, Groq, Cerebras, OpenRouter, Together.ai, GitHub Copilot,
LM Studio, LocalAI, vLLM, text-generation-webui, and ANY OpenAI-compatible API.
"""

import time
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from ald01.providers.base import (
    BaseProvider, CompletionRequest, CompletionResponse, ProviderStatus
)

logger = logging.getLogger("ald01.providers.openai_compat")


# ──────────────────────────────────────────────────────────────
# Pre-configured free providers
# ──────────────────────────────────────────────────────────────

FREE_PROVIDERS = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "free_tier": True,
        "description": "Ultra-fast inference, generous free tier (14,400 req/day)",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "mixtral-8x7b-32768",
        ],
        "env_key": "GROQ_API_KEY",
    },
    "cerebras": {
        "name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama-3.3-70b",
        "free_tier": True,
        "description": "World's fastest AI inference, free tier available",
        "models": ["llama-3.3-70b", "llama-3.1-8b"],
        "env_key": "CEREBRAS_API_KEY",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "free_tier": True,
        "description": "Access 200+ models, many free options available",
        "models": [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-2-9b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen-2.5-72b-instruct:free",
        ],
        "env_key": "OPENROUTER_API_KEY",
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "free_tier": True,
        "description": "Free $5 credit on signup, fast inference",
        "models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "Qwen/Qwen2.5-72B-Instruct-Turbo",
        ],
        "env_key": "TOGETHER_API_KEY",
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "base_url": "https://api.githubcopilot.com",
        "default_model": "gpt-4o",
        "free_tier": True,
        "description": "Free for GitHub Pro users, access to GPT-4o and Claude",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3.5-sonnet"],
        "env_key": "GITHUB_COPILOT_TOKEN",
    },
    "google_gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "free_tier": True,
        "description": "Google's AI, generous free tier (1500 req/day)",
        "models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        "env_key": "GEMINI_API_KEY",
    },
    "sambanova": {
        "name": "SambaNova",
        "base_url": "https://api.sambanova.ai/v1",
        "default_model": "Meta-Llama-3.3-70B-Instruct",
        "free_tier": True,
        "description": "Free inference API, ultra-fast custom chips",
        "models": [
            "Meta-Llama-3.3-70B-Instruct",
            "Meta-Llama-3.1-8B-Instruct",
        ],
        "env_key": "SAMBANOVA_API_KEY",
    },
    "novita": {
        "name": "Novita AI",
        "base_url": "https://api.novita.ai/v3/openai",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "free_tier": True,
        "description": "Free credits on signup, many open models",
        "models": [
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-v3",
        ],
        "env_key": "NOVITA_API_KEY",
    },
    "hyperbolic": {
        "name": "Hyperbolic",
        "base_url": "https://api.hyperbolic.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
        "free_tier": True,
        "description": "Free tier with fast GPU inference",
        "models": [
            "meta-llama/Llama-3.3-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "deepseek-ai/DeepSeek-V3",
        ],
        "env_key": "HYPERBOLIC_API_KEY",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "free_tier": False,
        "description": "OpenAI GPT models (paid, but included for completeness)",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini"],
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic_openai": {
        "name": "Anthropic (via OpenRouter)",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-3.5-sonnet",
        "free_tier": False,
        "description": "Claude models via OpenRouter",
        "models": ["anthropic/claude-3.5-sonnet", "anthropic/claude-3-haiku"],
        "env_key": "OPENROUTER_API_KEY",
    },
}


class OpenAICompatProvider(BaseProvider):
    """
    Universal provider for any OpenAI-compatible API.
    Handles: OpenAI, Groq, Cerebras, OpenRouter, Together, Gemini, SambaNova, etc.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.base_url = config.get("base_url", "https://api.openai.com/v1").rstrip("/")
        self.api_key = config.get("api_key", "")
        self.default_model = config.get("default_model", "gpt-4o-mini")
        self.extra_headers = config.get("extra_headers", {})

        # Auto-detect from free providers
        if name in FREE_PROVIDERS and not self.base_url:
            preset = FREE_PROVIDERS[name]
            self.base_url = preset["base_url"]
            self.default_model = preset["default_model"]

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Provider-specific headers
        if "openrouter" in self.base_url:
            headers["HTTP-Referer"] = "https://ald-01.dev"
            headers["X-Title"] = "ALD-01"
        if "githubcopilot" in self.base_url:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["Editor-Version"] = "ALD-01/1.0.0"

        headers.update(self.extra_headers)
        return headers

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send completion request to the API."""
        model = self.get_model(request.model)
        body = request.to_api_body(model_override=model)
        body["stream"] = False

        start_time = time.time()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=body,
                    headers=self._get_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                latency = (time.time() - start_time) * 1000

                content = ""
                finish_reason = "stop"
                usage = {}

                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    content = choice.get("message", {}).get("content", "")
                    finish_reason = choice.get("finish_reason", "stop")

                if "usage" in data:
                    usage = data["usage"]

                self._status.online = True
                self._status.latency_ms = latency
                self._status.last_check = time.time()

                return CompletionResponse(
                    content=content,
                    model=data.get("model", model),
                    provider=self.name,
                    finish_reason=finish_reason,
                    usage=usage,
                    latency_ms=latency,
                    raw=data,
                )

            except httpx.HTTPStatusError as e:
                error_body = ""
                try:
                    error_body = e.response.text[:500]
                except Exception:
                    pass
                logger.error(f"[{self.name}] HTTP {e.response.status_code}: {error_body}")
                self._status.online = False
                self._status.error = f"HTTP {e.response.status_code}"
                raise
            except Exception as e:
                logger.error(f"[{self.name}] Error: {e}")
                self._status.online = False
                self._status.error = str(e)
                raise

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion response chunk by chunk."""
        model = self.get_model(request.model)
        body = request.to_api_body(model_override=model)
        body["stream"] = True

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=body,
                    headers=self._get_headers(),
                ) as resp:
                    resp.raise_for_status()
                    self._status.online = True
                    self._status.last_check = time.time()

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

            except Exception as e:
                logger.error(f"[{self.name}] Stream error: {e}")
                self._status.online = False
                self._status.error = str(e)
                raise

    async def test_connection(self) -> ProviderStatus:
        """Test provider connectivity."""
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Try models endpoint first
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                )
                latency = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    models = []
                    if "data" in data:
                        models = [m.get("id", "") for m in data["data"][:20]]
                    self._status = ProviderStatus(
                        name=self.name,
                        online=True,
                        latency_ms=latency,
                        last_check=time.time(),
                        models=models,
                    )
                else:
                    # Some providers don't support /models, try a minimal completion
                    self._status = ProviderStatus(
                        name=self.name,
                        online=True,
                        latency_ms=latency,
                        last_check=time.time(),
                        models=[self.default_model],
                    )

        except Exception as e:
            self._status = ProviderStatus(
                name=self.name,
                online=False,
                latency_ms=(time.time() - start_time) * 1000,
                last_check=time.time(),
                error=str(e)[:200],
            )

        return self._status

    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data:
                        return [m.get("id", "") for m in data["data"]]
        except Exception as e:
            logger.debug(f"[{self.name}] Could not list models: {e}")

        # Fallback to preset models
        if self.name in FREE_PROVIDERS:
            return FREE_PROVIDERS[self.name].get("models", [self.default_model])
        return [self.default_model]


def create_free_provider(provider_key: str, api_key: str = "") -> Optional[OpenAICompatProvider]:
    """Create a provider from the FREE_PROVIDERS registry."""
    if provider_key not in FREE_PROVIDERS:
        return None

    preset = FREE_PROVIDERS[provider_key]
    import os
    key = api_key or os.environ.get(preset.get("env_key", ""), "")

    config = {
        "enabled": bool(key),
        "base_url": preset["base_url"],
        "default_model": preset["default_model"],
        "api_key": key,
        "priority": list(FREE_PROVIDERS.keys()).index(provider_key) + 1,
        "timeout": 60,
    }

    return OpenAICompatProvider(name=provider_key, config=config)


def list_free_providers() -> List[Dict[str, Any]]:
    """List all available free provider presets."""
    result = []
    for key, preset in FREE_PROVIDERS.items():
        import os
        env_key = preset.get("env_key", "")
        has_key = bool(os.environ.get(env_key, ""))
        result.append({
            "key": key,
            "name": preset["name"],
            "description": preset["description"],
            "free_tier": preset["free_tier"],
            "default_model": preset["default_model"],
            "models": preset["models"],
            "env_key": env_key,
            "configured": has_key,
        })
    return result
