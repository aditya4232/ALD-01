"""
ALD-01 Hardware Detection
Detect system hardware and recommend optimal brain power settings.
"""

import os
import platform
import logging
from typing import Any, Dict, Optional

import psutil

logger = logging.getLogger("ald01.hardware")


def detect_hardware() -> Dict[str, Any]:
    """Detect system hardware and return a comprehensive profile."""
    cpu_count_physical = psutil.cpu_count(logical=False) or 1
    cpu_count_logical = psutil.cpu_count() or 1
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.expanduser("~"))

    # CPU frequency
    cpu_freq = psutil.cpu_freq()
    freq_mhz = cpu_freq.current if cpu_freq else 0

    # GPU detection (best effort)
    gpu_info = _detect_gpu()

    profile = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "cpu": {
            "cores_physical": cpu_count_physical,
            "cores_logical": cpu_count_logical,
            "frequency_mhz": round(freq_mhz),
            "brand": platform.processor() or "Unknown",
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
        },
        "gpu": gpu_info,
    }

    # Calculate recommended brain power
    profile["recommended_brain_power"] = _recommend_brain_power(profile)

    return profile


def _detect_gpu() -> Dict[str, Any]:
    """Try to detect GPU (NVIDIA, AMD, Intel)."""
    gpu = {"available": False, "name": "None", "vram_gb": 0}

    # Try nvidia-smi
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines and lines[0]:
                parts = lines[0].split(",")
                gpu["available"] = True
                gpu["name"] = parts[0].strip()
                gpu["vram_gb"] = round(float(parts[1].strip()) / 1024, 1) if len(parts) > 1 else 0
                return gpu
    except Exception:
        pass

    return gpu


def _recommend_brain_power(profile: Dict[str, Any]) -> int:
    """Recommend brain power level based on hardware."""
    ram_gb = profile["memory"]["total_gb"]
    gpu = profile["gpu"]["available"]
    vram = profile["gpu"].get("vram_gb", 0)
    cores = profile["cpu"]["cores_physical"]

    # Scoring based on hardware
    if ram_gb < 4:
        return 1
    elif ram_gb < 8:
        return 2
    elif ram_gb < 16 and not gpu:
        return 3
    elif ram_gb < 16 and gpu:
        return 5
    elif ram_gb < 32 and not gpu:
        return 4
    elif ram_gb < 32 and gpu:
        if vram >= 8:
            return 7
        return 6
    elif ram_gb >= 32:
        if gpu and vram >= 16:
            return 9
        elif gpu and vram >= 8:
            return 8
        return 7
    return 5


def get_system_info_summary() -> str:
    """Get a one-line system summary."""
    profile = detect_hardware()
    gpu_str = f", GPU: {profile['gpu']['name']}" if profile['gpu']['available'] else ""
    return (
        f"{profile['platform']} | "
        f"{profile['cpu']['cores_logical']} cores | "
        f"{profile['memory']['total_gb']} GB RAM{gpu_str} | "
        f"Recommended Level: {profile['recommended_brain_power']}"
    )
