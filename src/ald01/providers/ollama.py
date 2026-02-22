"""
ALD-01 Ollama Provider
Direct integration with local Ollama instance for offline AI.
"""

import time
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from ald01.providers.base import (
    BaseProvider, CompletionRequest, CompletionResponse, ProviderStatus
)

logger = logging.getLogger("ald01.providers.ollama")


class OllamaProvider(BaseProvider):
    """
    Provider for locally-running Ollama.
    Supports both native Ollama API and OpenAI-compatible endpoint.
    """

    def __init__(self, name: str = "ollama", config: Optional[Dict[str, Any]] = None):
        config = config or {}
        config.setdefault("enabled", True)
        config.setdefault("priority", 1)
        config.setdefault("timeout", 120)
        config.setdefault("default_model", "llama3.2")
        super().__init__(name, config)
        self.host = config.get("host", "http://localhost:11434").rstrip("/")

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send completion via Ollama's OpenAI-compatible endpoint."""
        model = self.get_model(request.model)
        body = request.to_api_body(model_override=model)
        body["stream"] = False

        start_time = time.time()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.host}/v1/chat/completions",
                    json=body,
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

            except httpx.ConnectError:
                logger.warning(f"Ollama not running at {self.host}")
                self._status.online = False
                self._status.error = "Connection refused — is Ollama running?"
                raise ConnectionError(f"Ollama not available at {self.host}")
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                self._status.online = False
                self._status.error = str(e)
                raise

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion via Ollama's OpenAI-compatible endpoint."""
        model = self.get_model(request.model)
        body = request.to_api_body(model_override=model)
        body["stream"] = True

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.host}/v1/chat/completions",
                    json=body,
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
                logger.error(f"Ollama stream error: {e}")
                self._status.online = False
                self._status.error = str(e)
                raise

    async def test_connection(self) -> ProviderStatus:
        """Test Ollama connectivity and get available models."""
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.host}/api/tags")
                latency = (time.time() - start_time) * 1000

                models = []
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]

                self._status = ProviderStatus(
                    name=self.name,
                    online=True,
                    latency_ms=latency,
                    last_check=time.time(),
                    models=models,
                    metadata={"host": self.host, "model_count": len(models)},
                )
        except httpx.ConnectError:
            self._status = ProviderStatus(
                name=self.name,
                online=False,
                latency_ms=(time.time() - start_time) * 1000,
                last_check=time.time(),
                error="Ollama not running. Start with: ollama serve",
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
        """List locally available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Could not list Ollama models: {e}")
        return [self.default_model]

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from the Ollama library."""
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post(
                    f"{self.host}/api/pull",
                    json={"name": model_name},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a specific model."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.host}/api/show",
                    json={"name": model_name},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.debug(f"Could not get model info for {model_name}: {e}")
        return None
