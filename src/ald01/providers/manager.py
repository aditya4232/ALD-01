"""
ALD-01 Provider Manager
Manages multiple AI providers with automatic failover, load balancing, and connection testing.
"""

import os
import time
import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from ald01.config import get_config
from ald01.providers.base import (
    BaseProvider, CompletionRequest, CompletionResponse, ProviderStatus
)
from ald01.providers.ollama import OllamaProvider
from ald01.providers.openai_compat import OpenAICompatProvider, FREE_PROVIDERS, create_free_provider
from ald01.core.events import get_event_bus, Event, EventType

logger = logging.getLogger("ald01.providers.manager")


class ProviderManager:
    """
    Manages all configured AI providers with:
    - Automatic failover between providers
    - Priority-based routing
    - Connection testing and health monitoring
    - Dynamic provider registration
    """

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._event_bus = get_event_bus()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize providers from configuration."""
        if self._initialized:
            return

        config = get_config()

        # 1. Setup Ollama (always first)
        ollama_conf = config.get_provider_config("ollama")
        if ollama_conf and ollama_conf.get("enabled", True):
            self._providers["ollama"] = OllamaProvider(config=ollama_conf)

        # 2. Setup configured OpenAI-compatible providers
        for provider_name in ["openai", "anthropic"]:
            pconf = config.get_provider_config(provider_name)
            if pconf and pconf.get("enabled", False) and pconf.get("api_key", ""):
                self._providers[provider_name] = OpenAICompatProvider(
                    name=provider_name, config=pconf
                )

        # 3. Auto-detect free providers from environment variables
        for key, preset in FREE_PROVIDERS.items():
            if key in self._providers:
                continue
            env_key = preset.get("env_key", "")
            api_key = os.environ.get(env_key, "")
            if api_key:
                provider = create_free_provider(key, api_key)
                if provider:
                    self._providers[key] = provider
                    logger.info(f"Auto-detected provider: {preset['name']} (via {env_key})")

        # 4. Setup custom providers from config
        custom_providers = config.get("providers", "custom", default=[])
        if isinstance(custom_providers, list):
            for cp in custom_providers:
                if cp.get("enabled", False) and cp.get("name"):
                    name = cp["name"]
                    self._providers[name] = OpenAICompatProvider(name=name, config=cp)

        self._initialized = True
        logger.info(f"Initialized {len(self._providers)} provider(s): {list(self._providers.keys())}")

    def add_provider(self, name: str, provider: BaseProvider) -> None:
        """Add or replace a provider."""
        self._providers[name] = provider
        logger.info(f"Added provider: {name}")

    def remove_provider(self, name: str) -> bool:
        """Remove a provider."""
        if name in self._providers:
            del self._providers[name]
            return True
        return False

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get a specific provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def _get_sorted_providers(self) -> List[BaseProvider]:
        """Get providers sorted by priority (lower number = higher priority)."""
        return sorted(self._providers.values(), key=lambda p: p.priority)

    async def complete(self, request: CompletionRequest,
                       preferred_provider: Optional[str] = None) -> CompletionResponse:
        """
        Send a completion request with automatic failover.
        Tries the preferred provider first, then falls back through others by priority.
        """
        if not self._providers:
            raise RuntimeError("No providers configured. Run: ald-01 provider add <name>")

        # Build provider order
        providers_to_try: List[BaseProvider] = []

        if preferred_provider and preferred_provider in self._providers:
            providers_to_try.append(self._providers[preferred_provider])

        for p in self._get_sorted_providers():
            if p not in providers_to_try and p.enabled:
                providers_to_try.append(p)

        last_error = None
        for provider in providers_to_try:
            try:
                await self._event_bus.emit(Event(
                    type=EventType.PROVIDER_REQUEST,
                    data={"provider": provider.name, "model": request.model},
                    source="provider_manager",
                ))

                response = await provider.complete(request)

                await self._event_bus.emit(Event(
                    type=EventType.PROVIDER_RESPONSE,
                    data={
                        "provider": provider.name,
                        "model": response.model,
                        "latency_ms": response.latency_ms,
                    },
                    source="provider_manager",
                ))

                return response

            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider.name} failed: {e}. Trying next...")
                await self._event_bus.emit(Event(
                    type=EventType.PROVIDER_ERROR,
                    data={"provider": provider.name, "error": str(e)},
                    source="provider_manager",
                ))
                continue

        raise RuntimeError(
            f"All providers failed. Last error: {last_error}. "
            f"Tried: {[p.name for p in providers_to_try]}"
        )

    async def stream(self, request: CompletionRequest,
                     preferred_provider: Optional[str] = None) -> AsyncIterator[str]:
        """Stream a completion with automatic failover."""
        if not self._providers:
            raise RuntimeError("No providers configured.")

        providers_to_try: List[BaseProvider] = []
        if preferred_provider and preferred_provider in self._providers:
            providers_to_try.append(self._providers[preferred_provider])
        for p in self._get_sorted_providers():
            if p not in providers_to_try and p.enabled:
                providers_to_try.append(p)

        last_error = None
        for provider in providers_to_try:
            try:
                async for chunk in provider.stream(request):
                    yield chunk
                return  # Success
            except Exception as e:
                last_error = e
                logger.warning(f"Stream from {provider.name} failed: {e}. Trying next...")
                continue

        raise RuntimeError(f"All providers failed for streaming. Last: {last_error}")

    async def test_all(self) -> Dict[str, ProviderStatus]:
        """Test all provider connections."""
        results: Dict[str, ProviderStatus] = {}

        async def test_one(name: str, provider: BaseProvider):
            status = await provider.test_connection()
            results[name] = status
            event_type = EventType.PROVIDER_CONNECTED if status.online else EventType.PROVIDER_DISCONNECTED
            await self._event_bus.emit(Event(
                type=event_type,
                data=status.to_dict(),
                source="provider_manager",
            ))

        tasks = [test_one(n, p) for n, p in self._providers.items()]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def test_provider(self, name: str) -> Optional[ProviderStatus]:
        """Test a specific provider."""
        provider = self._providers.get(name)
        if not provider:
            return None
        return await provider.test_connection()

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers without testing."""
        return {name: p.status.to_dict() for name, p in self._providers.items()}

    async def get_best_provider(self) -> Optional[BaseProvider]:
        """Get the best available provider (online + lowest priority number)."""
        for provider in self._get_sorted_providers():
            if provider.status.online:
                return provider
        # If no status known, test all first
        await self.test_all()
        for provider in self._get_sorted_providers():
            if provider.status.online:
                return provider
        return None

    def add_free_provider(self, provider_key: str, api_key: str) -> bool:
        """Add a free provider by its key and API key."""
        provider = create_free_provider(provider_key, api_key)
        if provider:
            self._providers[provider_key] = provider
            return True
        return False

    def add_custom_provider(self, name: str, base_url: str, api_key: str = "",
                            model: str = "auto", priority: int = 50) -> None:
        """Add a custom OpenAI-compatible provider."""
        config = {
            "enabled": True,
            "base_url": base_url,
            "api_key": api_key,
            "default_model": model,
            "priority": priority,
            "timeout": 60,
        }
        self._providers[name] = OpenAICompatProvider(name=name, config=config)

    def get_stats(self) -> Dict[str, Any]:
        """Get provider manager statistics."""
        online = sum(1 for p in self._providers.values() if p.status.online)
        return {
            "total_providers": len(self._providers),
            "online_providers": online,
            "offline_providers": len(self._providers) - online,
            "providers": {n: p.status.to_dict() for n, p in self._providers.items()},
        }


# Singleton
_manager_instance: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get or create the global provider manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ProviderManager()
    return _manager_instance
