"""
ALD-01 Dashboard API Routes
REST API endpoints for the web dashboard pages:
Brain, Skills, Cron Jobs, SubAgents, Config, Settings, Worker, Notifications.
"""

import time
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("ald01.dashboard.api")

router = APIRouter(prefix="/api", tags=["dashboard"])


# ──────────────────────────────────────────────────────────────
# Brain
# ──────────────────────────────────────────────────────────────

@router.get("/brain")
async def get_brain_state():
    """Get full brain visualization data (nodes + connections)."""
    from ald01.core.brain import get_brain
    brain = get_brain()
    return brain.get_brain_state()


@router.get("/brain/stats")
async def get_brain_stats():
    from ald01.core.brain import get_brain
    return get_brain().get_stats()


@router.get("/brain/aptitudes")
async def get_aptitudes():
    from ald01.core.brain import get_brain
    return get_brain().get_aptitude_scores()


# ──────────────────────────────────────────────────────────────
# SubAgents
# ──────────────────────────────────────────────────────────────

@router.get("/subagents")
async def list_subagents():
    from ald01.core.subagents import get_subagent_registry
    return get_subagent_registry().list_agents()


@router.get("/subagents/stats")
async def subagent_stats():
    from ald01.core.subagents import get_subagent_registry
    return get_subagent_registry().get_stats()


@router.post("/subagents/{agent_id}/enable")
async def enable_subagent(agent_id: str):
    from ald01.core.subagents import get_subagent_registry
    ok = get_subagent_registry().enable_agent(agent_id)
    return {"success": ok}


@router.post("/subagents/{agent_id}/disable")
async def disable_subagent(agent_id: str):
    from ald01.core.subagents import get_subagent_registry
    ok = get_subagent_registry().disable_agent(agent_id)
    return {"success": ok}


# ──────────────────────────────────────────────────────────────
# Cron Jobs / Scheduler
# ──────────────────────────────────────────────────────────────

@router.get("/scheduler/jobs")
async def list_cron_jobs():
    from ald01.core.scheduler import get_scheduler
    return get_scheduler().list_jobs()


@router.post("/scheduler/jobs/{job_id}/enable")
async def enable_cron_job(job_id: str):
    from ald01.core.scheduler import get_scheduler
    return {"success": get_scheduler().enable_job(job_id)}


@router.post("/scheduler/jobs/{job_id}/disable")
async def disable_cron_job(job_id: str):
    from ald01.core.scheduler import get_scheduler
    return {"success": get_scheduler().disable_job(job_id)}


@router.delete("/scheduler/jobs/{job_id}")
async def delete_cron_job(job_id: str):
    from ald01.core.scheduler import get_scheduler
    return {"success": get_scheduler().remove_job(job_id)}


# ──────────────────────────────────────────────────────────────
# Background Worker
# ──────────────────────────────────────────────────────────────

@router.get("/worker/status")
async def worker_status():
    from ald01.core.worker import get_background_worker
    return get_background_worker().get_stats()


@router.get("/worker/jobs")
async def worker_jobs():
    from ald01.core.worker import get_background_worker
    return get_background_worker().get_recent_jobs()


@router.get("/worker/active")
async def worker_active_jobs():
    from ald01.core.worker import get_background_worker
    return get_background_worker().get_active_jobs()


# ──────────────────────────────────────────────────────────────
# Learning System
# ──────────────────────────────────────────────────────────────

@router.get("/learning/stats")
async def learning_stats():
    from ald01.core.learning import get_learning_system
    return get_learning_system().get_stats()


@router.get("/learning/patterns")
async def learning_patterns():
    from ald01.core.learning import get_learning_system
    return get_learning_system().get_patterns()


@router.get("/learning/recommendations")
async def learning_recommendations():
    from ald01.core.learning import get_learning_system
    return get_learning_system().get_recommendations()


# ──────────────────────────────────────────────────────────────
# Themes
# ──────────────────────────────────────────────────────────────

@router.get("/themes")
async def list_themes():
    from ald01.core.themes import get_theme_manager
    return get_theme_manager().list_themes()


@router.post("/themes/{theme_name}/activate")
async def activate_theme(theme_name: str):
    from ald01.core.themes import get_theme_manager
    try:
        theme = get_theme_manager().switch_theme(theme_name)
        return {"success": True, "theme": theme.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ──────────────────────────────────────────────────────────────
# Modes
# ──────────────────────────────────────────────────────────────

@router.get("/modes")
async def list_modes():
    from ald01.core.modes import get_mode_manager
    mm = get_mode_manager()
    return {
        "current": mm.current_mode.name,
        "modes": [m.to_dict() for m in mm.list_modes()],
    }


@router.post("/modes/{mode_name}/switch")
async def switch_mode(mode_name: str):
    from ald01.core.modes import get_mode_manager
    try:
        mode = get_mode_manager().switch_mode(mode_name)
        return {"success": True, "mode": mode.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ──────────────────────────────────────────────────────────────
# Status
# ──────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    from ald01.core.status import get_status_manager
    sm = get_status_manager()
    return sm.get_status_info()


@router.post("/status/{status_name}")
async def set_status(status_name: str):
    from ald01.core.status import get_status_manager
    try:
        get_status_manager().set_status(status_name)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────────────────────
# Multi-Model
# ──────────────────────────────────────────────────────────────

@router.get("/models")
async def get_model_config():
    from ald01.core.multi_model import get_multi_model
    return get_multi_model().get_config()


@router.get("/models/guide")
async def get_model_guide():
    from ald01.core.multi_model import get_multi_model
    return {"guide": get_multi_model().get_guide()}


# ──────────────────────────────────────────────────────────────
# Data Management
# ──────────────────────────────────────────────────────────────

@router.get("/data/storage")
async def data_storage_info():
    from ald01.core.data_manager import get_data_manager
    return get_data_manager().get_storage_info()


@router.get("/data/{category}")
async def list_data_files(category: str):
    from ald01.core.data_manager import get_data_manager
    return get_data_manager().list_files(category)


@router.delete("/data/temp")
async def reset_temp_data():
    from ald01.core.data_manager import get_data_manager
    return get_data_manager().reset_temp()


# ──────────────────────────────────────────────────────────────
# Notifications
# ──────────────────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications():
    from ald01.core.notifications import get_notification_manager
    return get_notification_manager().get_history()


@router.delete("/notifications")
async def clear_notifications():
    from ald01.core.notifications import get_notification_manager
    get_notification_manager().clear_history()
    return {"success": True}


# ──────────────────────────────────────────────────────────────
# Autostart
# ──────────────────────────────────────────────────────────────

@router.get("/autostart")
async def autostart_status():
    from ald01.core.autostart import get_autostart_manager
    return get_autostart_manager().get_status()


@router.post("/autostart/enable")
async def enable_autostart():
    from ald01.core.autostart import get_autostart_manager
    return get_autostart_manager().enable()


@router.post("/autostart/disable")
async def disable_autostart():
    from ald01.core.autostart import get_autostart_manager
    return get_autostart_manager().disable()


# ──────────────────────────────────────────────────────────────
# Plugins
# ──────────────────────────────────────────────────────────────

@router.get("/plugins")
async def list_plugins():
    from ald01.core.plugins import get_plugin_manager
    return get_plugin_manager().list_plugins()


@router.post("/plugins/{name}/enable")
async def enable_plugin(name: str):
    from ald01.core.plugins import get_plugin_manager
    return {"success": get_plugin_manager().enable_plugin(name)}


@router.post("/plugins/{name}/disable")
async def disable_plugin(name: str):
    from ald01.core.plugins import get_plugin_manager
    return {"success": get_plugin_manager().disable_plugin(name)}


# ──────────────────────────────────────────────────────────────
# Localization
# ──────────────────────────────────────────────────────────────

@router.get("/language")
async def get_language():
    from ald01.core.localization import get_localization
    loc = get_localization()
    return {
        "current": loc.current_language,
        "languages": loc.list_languages(),
    }


@router.post("/language/{lang_code}")
async def set_language(lang_code: str):
    from ald01.core.localization import get_localization
    ok = get_localization().set_language(lang_code)
    return {"success": ok}


# ──────────────────────────────────────────────────────────────
# Self-Healing / Doctor
# ──────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    from ald01.core.self_heal import get_self_healing_engine
    return get_self_healing_engine().run_health_check()


@router.get("/health/stats")
async def healing_stats():
    from ald01.core.self_heal import get_self_healing_engine
    return get_self_healing_engine().get_stats()


@router.get("/health/actions")
async def healing_actions():
    from ald01.core.self_heal import get_self_healing_engine
    return get_self_healing_engine().get_actions()


@router.post("/health/backup")
async def create_backup():
    from ald01.core.self_heal import get_self_healing_engine
    path = get_self_healing_engine().backup_data()
    return {"success": True, "path": path}


@router.post("/health/cleanup")
async def run_cleanup():
    from ald01.core.self_heal import get_self_healing_engine
    return get_self_healing_engine().cleanup_memory()


# ──────────────────────────────────────────────────────────────
# System Info
# ──────────────────────────────────────────────────────────────

@router.get("/system")
async def system_info():
    """Comprehensive system info for the dashboard."""
    import platform
    import psutil

    return {
        "timestamp": time.time(),
        "platform": platform.system(),
        "python": platform.python_version(),
        "cpu_percent": psutil.cpu_percent(),
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total_gb": round(psutil.disk_usage("/").total / (1024**3), 1) if platform.system() != "Windows" else round(psutil.disk_usage("C:\\").total / (1024**3), 1),
            "free_gb": round(psutil.disk_usage("/").free / (1024**3), 1) if platform.system() != "Windows" else round(psutil.disk_usage("C:\\").free / (1024**3), 1),
        },
    }


# ──────────────────────────────────────────────────────────────
# Benchmark
# ──────────────────────────────────────────────────────────────

@router.get("/benchmark/providers")
async def benchmark_providers():
    from ald01.providers.benchmark import PROVIDER_RATINGS
    return PROVIDER_RATINGS


@router.get("/benchmark/models")
async def benchmark_models():
    from ald01.providers.benchmark import MODEL_BRAIN_RATINGS
    return MODEL_BRAIN_RATINGS


@router.post("/benchmark/run")
async def run_benchmark():
    from ald01.providers.benchmark import benchmark_all_providers
    results = await benchmark_all_providers()
    return results
