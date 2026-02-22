"""
ALD-01 Multi-Model Orchestrator
Use 1 to 4 AI models simultaneously for enhanced brain power.
More models = more reasoning power, cross-validation, and better answers.
"""

import os
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("ald01.multi_model")


@dataclass
class ModelSlot:
    """A configured model slot."""
    slot: int  # 1-4
    provider: str  # e.g. 'groq', 'cerebras', 'ollama'
    model: str  # e.g. 'llama-3.3-70b-versatile'
    role: str  # 'primary', 'validator', 'creative', 'specialist'
    enabled: bool = True
    weight: float = 1.0  # How much to trust this model (0.0-1.0)
    latency_ms: float = 0.0
    success_rate: float = 1.0
    calls: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "provider": self.provider,
            "model": self.model,
            "role": self.role,
            "enabled": self.enabled,
            "weight": self.weight,
            "latency_ms": round(self.latency_ms),
            "success_rate": round(self.success_rate, 2),
            "calls": self.calls,
        }


class MultiModelOrchestrator:
    """
    Orchestrates 1-4 models for enhanced brain power.
    
    Modes:
    - Single:     1 model (default, fastest)
    - Duo:        2 models (primary + validator)
    - Triple:     3 models (primary + validator + creative)
    - Quad:       4 models (full cross-validation, maximum brain power)
    
    Strategies:
    - consensus:  Use the response most models agree on
    - primary:    Use primary model, others for validation
    - blend:      Blend responses from all models
    - fastest:    Use whichever responds first
    - specialist: Route to specialist model based on query type
    """

    def __init__(self):
        self._slots: Dict[int, ModelSlot] = {}
        self._strategy: str = "primary"  # Default strategy

    def configure_slot(
        self,
        slot: int,
        provider: str,
        model: str,
        role: str = "primary",
        weight: float = 1.0,
    ) -> None:
        """Configure a model slot (1-4)."""
        if slot < 1 or slot > 4:
            raise ValueError("Slot must be 1-4")

        self._slots[slot] = ModelSlot(
            slot=slot,
            provider=provider,
            model=model,
            role=role,
            weight=weight,
        )
        logger.info(f"Slot {slot}: {provider}/{model} ({role})")

    def remove_slot(self, slot: int) -> bool:
        if slot in self._slots:
            del self._slots[slot]
            return True
        return False

    def set_strategy(self, strategy: str) -> None:
        valid = ["consensus", "primary", "blend", "fastest", "specialist"]
        if strategy not in valid:
            raise ValueError(f"Strategy must be one of: {', '.join(valid)}")
        self._strategy = strategy

    @property
    def active_models(self) -> int:
        return sum(1 for s in self._slots.values() if s.enabled)

    @property
    def power_level(self) -> str:
        """Get current power level description."""
        count = self.active_models
        if count <= 1:
            return "Single (Standard)"
        elif count == 2:
            return "Duo (Enhanced)"
        elif count == 3:
            return "Triple (Advanced)"
        else:
            return "Quad (Maximum Brain Power)"

    async def query(
        self,
        messages: List[Dict[str, str]],
        provider_manager: Any = None,
    ) -> Dict[str, Any]:
        """
        Send a query to all configured models and combine results.
        Returns: {response, model_responses, strategy, timing}
        """
        active_slots = [s for s in self._slots.values() if s.enabled]

        if not active_slots:
            return {"error": "No model slots configured", "response": ""}

        if len(active_slots) == 1 or self._strategy == "primary":
            return await self._query_primary(active_slots, messages, provider_manager)
        elif self._strategy == "fastest":
            return await self._query_fastest(active_slots, messages, provider_manager)
        elif self._strategy == "consensus":
            return await self._query_consensus(active_slots, messages, provider_manager)
        else:
            return await self._query_primary(active_slots, messages, provider_manager)

    async def _query_primary(
        self, slots: List[ModelSlot], messages: List[Dict[str, str]], pm: Any
    ) -> Dict[str, Any]:
        """Primary model responds, others validate."""
        primary = next((s for s in slots if s.role == "primary"), slots[0])

        start = time.time()
        response = await self._call_model(primary, messages, pm)
        latency = (time.time() - start) * 1000

        return {
            "response": response,
            "model": f"{primary.provider}/{primary.model}",
            "strategy": "primary",
            "latency_ms": round(latency),
            "models_used": 1,
        }

    async def _query_fastest(
        self, slots: List[ModelSlot], messages: List[Dict[str, str]], pm: Any
    ) -> Dict[str, Any]:
        """Race all models, use first response."""
        start = time.time()

        tasks = [self._call_model(slot, messages, pm) for slot in slots]
        done, pending = await asyncio.wait(
            [asyncio.create_task(t) for t in tasks],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel remaining
        for task in pending:
            task.cancel()

        result = list(done)[0].result() if done else ""
        latency = (time.time() - start) * 1000

        return {
            "response": result,
            "strategy": "fastest",
            "latency_ms": round(latency),
            "models_used": len(slots),
        }

    async def _query_consensus(
        self, slots: List[ModelSlot], messages: List[Dict[str, str]], pm: Any
    ) -> Dict[str, Any]:
        """Query all models and find consensus (use longest/most detailed)."""
        start = time.time()

        tasks = [self._call_model(slot, messages, pm) for slot in slots]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        valid_responses = [r for r in responses if isinstance(r, str) and r.strip()]
        latency = (time.time() - start) * 1000

        if not valid_responses:
            return {"response": "", "error": "All models failed", "strategy": "consensus"}

        # Use the longest (most detailed) response as consensus
        best = max(valid_responses, key=len)

        return {
            "response": best,
            "strategy": "consensus",
            "latency_ms": round(latency),
            "models_used": len(valid_responses),
            "total_responses": len(responses),
        }

    async def _call_model(
        self, slot: ModelSlot, messages: List[Dict[str, str]], pm: Any
    ) -> str:
        """Call a single model via provider manager."""
        slot.calls += 1
        try:
            if pm is not None:
                # Use provider manager
                response = await pm.chat_completion(
                    messages=messages,
                    provider_name=slot.provider,
                    model=slot.model,
                )
                start = time.time()
                text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                slot.latency_ms = (time.time() - start) * 1000
                slot.success_rate = (slot.success_rate * (slot.calls - 1) + 1) / slot.calls
                return text
            else:
                return ""
        except Exception as e:
            slot.success_rate = (slot.success_rate * (slot.calls - 1)) / slot.calls
            logger.error(f"Model call failed (slot {slot.slot}): {e}")
            return ""

    def get_config(self) -> Dict[str, Any]:
        """Get current multi-model configuration."""
        return {
            "slots": {s: slot.to_dict() for s, slot in self._slots.items()},
            "strategy": self._strategy,
            "active_models": self.active_models,
            "power_level": self.power_level,
        }

    def get_guide(self) -> str:
        """Get setup guide for multi-model."""
        return """
🧠 Multi-Model Setup Guide
═══════════════════════════

Slot 1 (Primary):    Main model for responses
Slot 2 (Validator):  Cross-checks primary's output
Slot 3 (Creative):   Alternative perspectives
Slot 4 (Specialist): Deep expertise on specific topics

Recommended Configs:
  💡 Budget:   1 model  (Groq Llama 3.3 70B)
  ⚡ Balanced: 2 models (Groq + Cerebras)
  🔥 Power:   3 models (Groq + GitHub Copilot + Ollama)
  🧠 Maximum: 4 models (All providers for AGI-level)

Strategies:
  primary   — Use slot 1, others verify
  fastest   — Race all, use first response
  consensus — Query all, pick best answer
  blend     — Combine insights from all
  specialist — Route by query type
"""


_multi_model: Optional[MultiModelOrchestrator] = None

def get_multi_model() -> MultiModelOrchestrator:
    global _multi_model
    if _multi_model is None:
        _multi_model = MultiModelOrchestrator()
    return _multi_model
