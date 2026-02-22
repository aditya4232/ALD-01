"""
ALD-01 Dashboard API Extension Router
Bridges core subsystems to the frontend: brain, scheduler, language, themes,
data manager, autostart, multi-model, notifications, worker, status.
"""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("ald01.dashboard.api_ext")

router = APIRouter(prefix="/api/ext", tags=["extensions"])


# ──────────────────────────────────────────────────────────────
# Brain
# ──────────────────────────────────────────────────────────────

@router.get("/brain")
async def get_brain_data():
    """Full brain state for visualization."""
    try:
        from ald01.core.brain import get_brain
        brain = get_brain()
        return brain.get_visualization_data()
    except Exception as e:
        return {
            "nodes": [],
            "connections": [],
            "stats": {
                "total_nodes": 0,
                "total_connections": 0,
                "skills_count": 0,
                "growth_rate": 0,
            },
            "error": str(e),
        }


@router.get("/brain/stats")
async def get_brain_stats():
    try:
        from ald01.core.brain import get_brain
        return get_brain().get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/brain/learn")
async def brain_learn(request: Request):
    """Teach the brain a new topic."""
    body = await request.json()
    topic = body.get("topic", "")
    strength = body.get("strength", 0.3)
    if not topic:
        raise HTTPException(400, "Missing topic")
    try:
        from ald01.core.brain import get_brain
        get_brain().learn_topic(topic, strength)
        return {"success": True, "topic": topic}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Scheduler / Cron
# ──────────────────────────────────────────────────────────────

@router.get("/scheduler/jobs")
async def list_scheduler_jobs():
    try:
        from ald01.core.scheduler import get_scheduler
        return {"jobs": get_scheduler().list_jobs()}
    except Exception as e:
        return {"jobs": [], "error": str(e)}


@router.post("/scheduler/jobs")
async def add_scheduler_job(request: Request):
    body = await request.json()
    try:
        from ald01.core.scheduler import get_scheduler
        job = get_scheduler().add_job(
            name=body.get("name", "custom"),
            schedule=body.get("schedule", "0 * * * *"),
            action=body.get("action", ""),
        )
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/scheduler/jobs/{job_id}")
async def remove_scheduler_job(job_id: str):
    try:
        from ald01.core.scheduler import get_scheduler
        return {"success": get_scheduler().remove_job(job_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Language / Localization
# ──────────────────────────────────────────────────────────────

@router.get("/language")
async def get_language():
    try:
        from ald01.core.localization import get_localization
        loc = get_localization()
        return {
            "current": loc.current_language,
            "available": loc.available_languages(),
        }
    except Exception as e:
        return {"current": "en", "error": str(e)}


@router.post("/language/{lang}")
async def set_language(lang: str):
    try:
        from ald01.core.localization import get_localization
        get_localization().set_language(lang)
        return {"success": True, "language": lang}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Themes
# ──────────────────────────────────────────────────────────────

@router.get("/themes")
async def list_themes():
    try:
        from ald01.core.themes import get_theme_manager
        tm = get_theme_manager()
        return {
            "current": tm.get_current_theme_name(),
            "available": tm.list_themes(),
        }
    except Exception as e:
        return {"current": "cyberpunk", "available": [], "error": str(e)}


@router.post("/themes/{theme_name}")
async def set_theme(theme_name: str):
    try:
        from ald01.core.themes import get_theme_manager
        result = get_theme_manager().set_theme(theme_name)
        return {"success": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Modes
# ──────────────────────────────────────────────────────────────

@router.get("/modes")
async def list_modes():
    try:
        from ald01.core.modes import get_mode_manager
        mm = get_mode_manager()
        return {
            "current": mm.get_current_mode_name(),
            "available": mm.list_modes(),
        }
    except Exception as e:
        return {"current": "default", "available": [], "error": str(e)}


@router.post("/modes/{mode_name}")
async def set_mode(mode_name: str):
    try:
        from ald01.core.modes import get_mode_manager
        result = get_mode_manager().set_mode(mode_name)
        return {"success": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Status
# ──────────────────────────────────────────────────────────────

@router.get("/user-status")
async def get_user_status():
    try:
        from ald01.core.status import get_status_manager
        sm = get_status_manager()
        return {
            "current": sm.get_current_status(),
            "available": sm.list_statuses(),
        }
    except Exception as e:
        return {"current": "open", "error": str(e)}


@router.post("/user-status/{status}")
async def set_user_status(status: str):
    try:
        from ald01.core.status import get_status_manager
        get_status_manager().set_status(status)
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Data Manager
# ──────────────────────────────────────────────────────────────

@router.get("/data/storage")
async def get_storage_info():
    try:
        from ald01.core.data_manager import get_data_manager
        return get_data_manager().get_storage_info()
    except Exception as e:
        return {"error": str(e)}


@router.post("/data/cleanup/{category}")
async def cleanup_data(category: str):
    """category: 'temp', 'normal', 'important'"""
    if category not in ("temp", "normal"):
        raise HTTPException(400, "Can only clean temp or normal data")
    try:
        from ald01.core.data_manager import get_data_manager
        result = get_data_manager().cleanup(category)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Autostart
# ──────────────────────────────────────────────────────────────

@router.get("/autostart")
async def get_autostart():
    try:
        from ald01.core.autostart import get_autostart_manager
        return {"enabled": get_autostart_manager().is_enabled()}
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@router.post("/autostart/{action}")
async def toggle_autostart(action: str):
    """action: 'enable' or 'disable'"""
    try:
        from ald01.core.autostart import get_autostart_manager
        mgr = get_autostart_manager()
        if action == "enable":
            mgr.enable()
        elif action == "disable":
            mgr.disable()
        else:
            raise HTTPException(400, "Use 'enable' or 'disable'")
        return {"success": True, "enabled": mgr.is_enabled()}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Multi-Model
# ──────────────────────────────────────────────────────────────

@router.get("/multi-model")
async def get_multi_model():
    try:
        from ald01.core.multi_model import get_multi_model
        return get_multi_model().get_config()
    except Exception as e:
        return {"error": str(e)}


@router.post("/multi-model/strategy")
async def set_strategy(request: Request):
    body = await request.json()
    try:
        from ald01.core.multi_model import get_multi_model
        get_multi_model().set_strategy(body.get("strategy", "primary"))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Notifications
# ──────────────────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications():
    try:
        from ald01.core.notifications import get_notification_manager
        nm = get_notification_manager()
        return {
            "history": nm.get_history()[-50:],
            "count": len(nm.get_history()),
        }
    except Exception as e:
        return {"history": [], "error": str(e)}


@router.post("/notifications/send")
async def send_notification(request: Request):
    body = await request.json()
    try:
        from ald01.core.notifications import get_notification_manager
        get_notification_manager().notify(
            title=body.get("title", "ALD-01"),
            message=body.get("message", ""),
            level=body.get("level", "info"),
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/notifications")
async def clear_notifications():
    try:
        from ald01.core.notifications import get_notification_manager
        get_notification_manager().clear_history()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Background Worker
# ──────────────────────────────────────────────────────────────

@router.get("/worker/tasks")
async def get_worker_tasks():
    try:
        from ald01.core.worker import get_background_worker
        worker = get_background_worker()
        return {
            "queue_size": worker.queue_size(),
            "completed": worker.completed_count(),
            "running": worker.is_running(),
        }
    except Exception as e:
        return {"queue_size": 0, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Self-Healing
# ──────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    try:
        from ald01.core.self_heal import get_self_healing_engine
        return get_self_healing_engine().run_health_check()
    except Exception as e:
        return {"healthy": False, "error": str(e)}


@router.post("/health/repair")
async def auto_repair():
    try:
        from ald01.core.self_heal import get_self_healing_engine
        return get_self_healing_engine().auto_repair()
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Config Editor
# ──────────────────────────────────────────────────────────────

@router.get("/config/all")
async def get_all_config():
    try:
        from ald01.core.config_editor import get_config_editor
        return get_config_editor().get_all()
    except Exception as e:
        return {"error": str(e)}


@router.get("/config/categories")
async def get_config_categories():
    try:
        from ald01.core.config_editor import get_config_editor
        return get_config_editor().get_categories()
    except Exception as e:
        return {"error": str(e)}


@router.post("/config")
async def update_config(request: Request):
    body = await request.json()
    try:
        from ald01.core.config_editor import get_config_editor
        return get_config_editor().set_multiple(body)
    except Exception as e:
        return {"error": str(e)}


@router.post("/config/reset")
async def reset_config():
    try:
        from ald01.core.config_editor import get_config_editor
        return get_config_editor().reset_all()
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# Plugins
# ──────────────────────────────────────────────────────────────

@router.get("/plugins")
async def list_plugins():
    try:
        from ald01.core.plugins import get_plugin_manager
        return get_plugin_manager().list_plugins()
    except Exception as e:
        return {"plugins": [], "error": str(e)}


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    try:
        from ald01.core.plugins import get_plugin_manager
        return {"success": get_plugin_manager().enable_plugin(plugin_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    try:
        from ald01.core.plugins import get_plugin_manager
        return {"success": get_plugin_manager().disable_plugin(plugin_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# SubAgents
# ──────────────────────────────────────────────────────────────

@router.get("/subagents")
async def list_subagents():
    try:
        from ald01.core.subagents import get_subagent_registry
        return get_subagent_registry().list_agents()
    except Exception as e:
        return {"agents": [], "error": str(e)}


@router.post("/subagents/{agent_id}/toggle")
async def toggle_subagent(agent_id: str):
    try:
        from ald01.core.subagents import get_subagent_registry
        return {"success": get_subagent_registry().toggle_agent(agent_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Learning
# ──────────────────────────────────────────────────────────────

@router.get("/learning/stats")
async def learning_stats():
    try:
        from ald01.core.learning import get_learning_system
        return get_learning_system().get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/learning/patterns")
async def learned_patterns():
    try:
        from ald01.core.learning import get_learning_system
        return {"patterns": get_learning_system().get_patterns()}
    except Exception as e:
        return {"patterns": [], "error": str(e)}
