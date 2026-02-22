"""
ALD-01 Provider Benchmark
Benchmarks AI providers for speed, quality, and brain power rating.
Shows visual bars during onboarding to help users pick the best provider.
"""

import time
import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from ald01.providers.openai_compat import FREE_PROVIDERS

logger = logging.getLogger("ald01.benchmark")


# Brain power ratings for models (how capable they are)
MODEL_BRAIN_RATINGS: Dict[str, Dict[str, Any]] = {
    # Tier 1 — Maximum brain power
    "gpt-4o": {"brain": 95, "reasoning": 95, "coding": 95, "speed": 70, "tier": "S"},
    "gpt-4.1": {"brain": 95, "reasoning": 95, "coding": 97, "speed": 72, "tier": "S"},
    "claude-3.5-sonnet": {"brain": 94, "reasoning": 93, "coding": 96, "speed": 72, "tier": "S"},
    "claude-3-opus": {"brain": 96, "reasoning": 96, "coding": 95, "speed": 55, "tier": "S"},
    "gemini-2.0-flash": {"brain": 85, "reasoning": 82, "coding": 83, "speed": 90, "tier": "A"},
    "gemini-2.5-pro": {"brain": 93, "reasoning": 90, "coding": 92, "speed": 65, "tier": "S"},
    "deepseek-r1": {"brain": 92, "reasoning": 94, "coding": 93, "speed": 50, "tier": "S"},
    
    # Tier 2 — Strong brain power
    "llama-3.3-70b-versatile": {"brain": 88, "reasoning": 85, "coding": 87, "speed": 92, "tier": "A"},
    "llama-3.3-70b": {"brain": 88, "reasoning": 85, "coding": 87, "speed": 80, "tier": "A"},
    "llama-3.1-70b": {"brain": 85, "reasoning": 82, "coding": 84, "speed": 78, "tier": "A"},
    "qwen-2.5-72b": {"brain": 86, "reasoning": 84, "coding": 86, "speed": 75, "tier": "A"},
    "mixtral-8x7b": {"brain": 78, "reasoning": 76, "coding": 78, "speed": 85, "tier": "B"},
    "codestral-latest": {"brain": 80, "reasoning": 75, "coding": 90, "speed": 82, "tier": "A"},
    
    # Tier 3 — Good brain power
    "llama-3.2-3b": {"brain": 55, "reasoning": 50, "coding": 52, "speed": 98, "tier": "C"},
    "llama-3.1-8b": {"brain": 65, "reasoning": 60, "coding": 63, "speed": 95, "tier": "B"},
    "llama-3-8b": {"brain": 62, "reasoning": 58, "coding": 60, "speed": 96, "tier": "B"},
    "phi-3-mini": {"brain": 58, "reasoning": 55, "coding": 60, "speed": 95, "tier": "C"},
    "gemma-2-9b": {"brain": 63, "reasoning": 60, "coding": 62, "speed": 90, "tier": "B"},
    
    # Tier 4 — Small models
    "tinyllama": {"brain": 30, "reasoning": 25, "coding": 25, "speed": 99, "tier": "D"},
    "phi-2": {"brain": 45, "reasoning": 40, "coding": 48, "speed": 97, "tier": "D"},
}

# Provider rankings (overall quality of the provider service)
PROVIDER_RATINGS: Dict[str, Dict[str, Any]] = {
    "groq": {
        "display": "Groq",
        "speed": 98,       # Blazing fast LPU
        "reliability": 90,
        "models": 85,
        "free_tier": 95,    # Very generous
        "best_for": "Speed — fastest inference, great free tier",
        "brain_power_note": "Llama 3.3 70B gives excellent brain power with insane speed",
        "recommended": True,
    },
    "cerebras": {
        "display": "Cerebras",
        "speed": 95,
        "reliability": 85,
        "models": 75,
        "free_tier": 85,
        "best_for": "Speed — wafer-scale AI chips, very fast",
        "brain_power_note": "Llama 3.3 70B for strong reasoning at high speed",
        "recommended": True,
    },
    "github_copilot": {
        "display": "GitHub Copilot",
        "speed": 75,
        "reliability": 95,
        "models": 90,
        "free_tier": 80,
        "best_for": "Quality — GPT-4.1 for maximum brain power (free for Pro users)",
        "brain_power_note": "GPT-4.1 is one of the most capable models available",
        "recommended": True,
    },
    "openrouter": {
        "display": "OpenRouter",
        "speed": 75,
        "reliability": 88,
        "models": 98,
        "free_tier": 70,
        "best_for": "Variety — access to 200+ models from one API",
        "brain_power_note": "Access to Claude, GPT-4, and all top models",
        "recommended": False,
    },
    "together_ai": {
        "display": "Together AI",
        "speed": 82,
        "reliability": 87,
        "models": 88,
        "free_tier": 80,
        "best_for": "Open-source models — good Mixtral and Llama access",
        "brain_power_note": "Mixtral 8x7B for balanced speed and quality",
        "recommended": False,
    },
    "google_gemini": {
        "display": "Google Gemini",
        "speed": 80,
        "reliability": 92,
        "models": 82,
        "free_tier": 90,
        "best_for": "Multimodal — vision + text, generous free tier",
        "brain_power_note": "Gemini 2.0 Flash for fast, capable reasoning",
        "recommended": True,
    },
    "sambanova": {
        "display": "SambaNova",
        "speed": 85,
        "reliability": 80,
        "models": 70,
        "free_tier": 85,
        "best_for": "Speed — custom AI chips, fast Llama inference",
        "brain_power_note": "Llama 3.1 variants with good speed",
        "recommended": False,
    },
    "ollama": {
        "display": "Ollama (Local)",
        "speed": 60,
        "reliability": 99,
        "models": 95,
        "free_tier": 100,
        "best_for": "Privacy — 100% local, no API key needed",
        "brain_power_note": "Depends on your GPU. With 16GB+ VRAM, run 70B models locally",
        "recommended": True,
    },
    "novita_ai": {
        "display": "Novita AI",
        "speed": 78,
        "reliability": 78,
        "models": 72,
        "free_tier": 75,
        "best_for": "Budget — free credits for experimentation",
        "brain_power_note": "Llama 3 8B for lightweight tasks",
        "recommended": False,
    },
    "hyperbolic": {
        "display": "Hyperbolic",
        "speed": 70,
        "reliability": 75,
        "models": 65,
        "free_tier": 70,
        "best_for": "Reasoning — DeepSeek R1 for deep chain-of-thought",
        "brain_power_note": "DeepSeek R1 has excellent reasoning ability",
        "recommended": False,
    },
}


def get_model_brain_rating(model: str) -> Dict[str, Any]:
    """Get brain power rating for a model."""
    # Direct match
    if model in MODEL_BRAIN_RATINGS:
        return MODEL_BRAIN_RATINGS[model]

    # Fuzzy match
    model_lower = model.lower()
    for key, rating in MODEL_BRAIN_RATINGS.items():
        if key in model_lower or model_lower in key:
            return rating

    # Estimate based on model name
    if "70b" in model_lower or "72b" in model_lower:
        return {"brain": 85, "reasoning": 82, "coding": 84, "speed": 70, "tier": "A"}
    elif "34b" in model_lower or "33b" in model_lower:
        return {"brain": 72, "reasoning": 68, "coding": 70, "speed": 80, "tier": "B"}
    elif "13b" in model_lower or "14b" in model_lower:
        return {"brain": 65, "reasoning": 60, "coding": 62, "speed": 88, "tier": "B"}
    elif "8b" in model_lower or "7b" in model_lower or "9b" in model_lower:
        return {"brain": 58, "reasoning": 55, "coding": 55, "speed": 92, "tier": "C"}
    elif "3b" in model_lower or "2b" in model_lower or "1b" in model_lower:
        return {"brain": 40, "reasoning": 35, "coding": 35, "speed": 98, "tier": "D"}

    return {"brain": 50, "reasoning": 50, "coding": 50, "speed": 50, "tier": "C"}


def get_provider_rating(provider: str) -> Dict[str, Any]:
    """Get provider rating info."""
    return PROVIDER_RATINGS.get(provider, {
        "display": provider,
        "speed": 50, "reliability": 50, "models": 50, "free_tier": 50,
        "best_for": "Unknown", "brain_power_note": "", "recommended": False,
    })


def render_bar(value: int, max_val: int = 100, width: int = 20, fill: str = "█", empty: str = "░") -> str:
    """Render a progress bar string."""
    filled = int((value / max_val) * width)
    return fill * filled + empty * (width - filled)


def render_provider_comparison() -> str:
    """Render a text-based provider comparison table for the terminal."""
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════════════╗")
    lines.append("║           🧠 ALD-01 Provider Brain Power Comparison                ║")
    lines.append("╠══════════════════════════════════════════════════════════════════════╣")

    # Sort by best_for relevance
    sorted_providers = sorted(
        PROVIDER_RATINGS.items(),
        key=lambda x: (not x[1]["recommended"], -x[1]["speed"]),
    )

    for key, info in sorted_providers:
        star = "⭐" if info["recommended"] else "  "
        name = f"{info['display']:16s}"
        speed_bar = render_bar(info["speed"], width=10)
        reliability_bar = render_bar(info["reliability"], width=10)
        models_bar = render_bar(info["models"], width=10)
        free_bar = render_bar(info["free_tier"], width=10)

        lines.append(f"║ {star} {name}                                                    ║")
        lines.append(f"║    Speed:      {speed_bar} {info['speed']:3d}%                        ║")
        lines.append(f"║    Reliability: {reliability_bar} {info['reliability']:3d}%                        ║")
        lines.append(f"║    Models:      {models_bar} {info['models']:3d}%                        ║")
        lines.append(f"║    Free Tier:   {free_bar} {info['free_tier']:3d}%                        ║")
        lines.append(f"║    Best for: {info['best_for'][:55]:55s}  ║")
        lines.append(f"║    Brain: {info['brain_power_note'][:58]:58s}  ║")
        lines.append("║──────────────────────────────────────────────────────────────────────║")

    lines.append("║  ⭐ = Recommended for ALD-01                                       ║")
    lines.append("╚══════════════════════════════════════════════════════════════════════╝")

    return "\n".join(lines)


async def benchmark_provider(
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    """Benchmark a single provider for latency and availability."""
    result = {
        "model": model,
        "available": False,
        "latency_ms": 0,
        "tokens_per_second": 0,
        "error": "",
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'hello' in one word."}],
        "max_tokens": 10,
        "temperature": 0,
    }

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                result["available"] = True
                result["latency_ms"] = round(elapsed)
                if total_tokens > 0 and elapsed > 0:
                    result["tokens_per_second"] = round(total_tokens / (elapsed / 1000), 1)
            else:
                result["error"] = f"HTTP {resp.status_code}"

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


async def benchmark_all_providers() -> List[Dict[str, Any]]:
    """Benchmark all configured providers."""
    import os
    results = []

    for key, preset in FREE_PROVIDERS.items():
        env_key = preset.get("env_key", "")
        api_key = os.environ.get(env_key, "")

        if not api_key:
            results.append({
                "provider": key,
                "display": preset["name"],
                "available": False,
                "reason": "No API key",
            })
            continue

        bench = await benchmark_provider(
            base_url=preset["base_url"],
            api_key=api_key,
            model=preset["default_model"],
        )
        bench["provider"] = key
        bench["display"] = preset["name"]
        results.append(bench)

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                results.append({
                    "provider": "ollama",
                    "display": "Ollama (Local)",
                    "available": True,
                    "latency_ms": 0,
                    "reason": "Local — no network latency",
                })
    except Exception:
        results.append({
            "provider": "ollama",
            "display": "Ollama (Local)",
            "available": False,
            "reason": "Not running",
        })

    results.sort(key=lambda x: (not x.get("available", False), x.get("latency_ms", 9999)))
    return results
