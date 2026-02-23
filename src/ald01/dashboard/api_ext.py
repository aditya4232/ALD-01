"""
ALD-01 Dashboard API Extension Router
Bridges core subsystems to the frontend: brain, scheduler, language, themes,
data manager, autostart, multi-model, notifications, worker, status.
"""

import os
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


# ──────────────────────────────────────────────────────────────
# Backup Manager
# ──────────────────────────────────────────────────────────────

@router.get("/backups")
async def list_backups():
    try:
        from ald01.core.backup_manager import get_backup_manager
        return {"backups": get_backup_manager().list_backups()}
    except Exception as e:
        return {"backups": [], "error": str(e)}


@router.post("/backups")
async def create_backup(request: Request):
    body = await request.json()
    try:
        from ald01.core.backup_manager import get_backup_manager
        return get_backup_manager().create_backup(
            backup_type=body.get("type", "full"),
            label=body.get("label", ""),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/backups/{name}/restore")
async def restore_backup(name: str):
    try:
        from ald01.core.backup_manager import get_backup_manager
        return get_backup_manager().restore_backup(name)
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/backups/{name}")
async def delete_backup(name: str):
    try:
        from ald01.core.backup_manager import get_backup_manager
        return {"success": get_backup_manager().delete_backup(name)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/backups/stats")
async def backup_stats():
    try:
        from ald01.core.backup_manager import get_backup_manager
        return get_backup_manager().get_stats()
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# Analytics
# ──────────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics():
    try:
        from ald01.core.analytics import get_analytics
        return get_analytics().get_dashboard_data()
    except Exception as e:
        return {"error": str(e)}


@router.get("/analytics/health")
async def analytics_health():
    try:
        from ald01.core.analytics import get_analytics
        return get_analytics().get_health_metrics()
    except Exception as e:
        return {"error": str(e)}


@router.get("/analytics/costs")
async def get_cost_summary():
    try:
        from ald01.core.analytics import get_analytics
        return get_analytics().cost_tracker.get_summary(24)
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# Command Executor
# ──────────────────────────────────────────────────────────────

@router.post("/execute")
async def execute_command(request: Request):
    body = await request.json()
    command = body.get("command", "")
    if not command:
        raise HTTPException(400, "Missing command")
    try:
        from ald01.core.executor import get_executor
        result = await get_executor().execute(
            command, cwd=body.get("cwd"),
            timeout=body.get("timeout", 30),
        )
        return result.to_dict()
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/execute/history")
async def command_history():
    try:
        from ald01.core.executor import get_executor
        return {"history": get_executor().get_history()}
    except Exception as e:
        return {"history": [], "error": str(e)}


@router.get("/execute/running")
async def running_processes():
    try:
        from ald01.core.executor import get_executor
        return {"processes": get_executor().get_running()}
    except Exception as e:
        return {"processes": [], "error": str(e)}


@router.delete("/execute/{pid}")
async def kill_process(pid: int):
    try:
        from ald01.core.executor import get_executor
        return {"success": await get_executor().kill_process(pid)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────

@router.get("/webhooks")
async def list_webhooks():
    try:
        from ald01.core.webhooks import get_webhook_engine
        return {"webhooks": get_webhook_engine().list_subscriptions()}
    except Exception as e:
        return {"webhooks": [], "error": str(e)}


@router.post("/webhooks")
async def register_webhook(request: Request):
    body = await request.json()
    try:
        from ald01.core.webhooks import get_webhook_engine
        return get_webhook_engine().register(
            url=body.get("url", ""),
            events=body.get("events", ["*"]),
            secret=body.get("secret", ""),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/webhooks/{webhook_id}")
async def unregister_webhook(webhook_id: str):
    try:
        from ald01.core.webhooks import get_webhook_engine
        return {"success": get_webhook_engine().unregister(webhook_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/webhooks/events")
async def webhook_events():
    try:
        from ald01.core.webhooks import get_webhook_engine
        return {"events": get_webhook_engine().get_available_events()}
    except Exception as e:
        return {"events": [], "error": str(e)}


@router.get("/webhooks/deliveries")
async def webhook_deliveries():
    try:
        from ald01.core.webhooks import get_webhook_engine
        return {"deliveries": get_webhook_engine().get_deliveries(50)}
    except Exception as e:
        return {"deliveries": [], "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Code Analyzer
# ──────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_code(request: Request):
    body = await request.json()
    path = body.get("path", "")
    if not path:
        raise HTTPException(400, "Missing path")
    try:
        from ald01.core.code_analyzer import get_code_analyzer
        analyzer = get_code_analyzer()
        if os.path.isdir(path):
            return analyzer.analyze_directory(path)
        elif os.path.isfile(path):
            return analyzer.analyze_file(path).to_dict()
        else:
            return {"error": f"Path not found: {path}"}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# API Gateway
# ──────────────────────────────────────────────────────────────

@router.get("/gateway/keys")
async def list_api_keys():
    try:
        from ald01.core.gateway import get_api_gateway
        return {"keys": get_api_gateway().list_keys()}
    except Exception as e:
        return {"keys": [], "error": str(e)}


@router.post("/gateway/keys")
async def create_api_key(request: Request):
    body = await request.json()
    try:
        from ald01.core.gateway import get_api_gateway
        return get_api_gateway().generate_api_key(
            name=body.get("name", "default"),
            permissions=body.get("permissions", ["read"]),
            rate_limit=body.get("rate_limit", 60),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/gateway/keys/{key_id}")
async def delete_api_key(key_id: str):
    try:
        from ald01.core.gateway import get_api_gateway
        return {"success": get_api_gateway().delete_key(key_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/gateway/stats")
async def gateway_stats():
    try:
        from ald01.core.gateway import get_api_gateway
        return get_api_gateway().get_stats()
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# Export System
# ──────────────────────────────────────────────────────────────

@router.get("/exports")
async def list_exports():
    try:
        from ald01.core.export_system import get_export_system
        return {"exports": get_export_system().list_exports()}
    except Exception as e:
        return {"exports": [], "error": str(e)}


@router.post("/exports/conversation")
async def export_conversation(request: Request):
    body = await request.json()
    try:
        from ald01.core.export_system import get_export_system
        return get_export_system().export_conversation(
            messages=body.get("messages", []),
            title=body.get("title", "Conversation"),
            format=body.get("format", "markdown"),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/exports/status")
async def export_status():
    try:
        from ald01.core.export_system import get_export_system
        from ald01.dashboard.server import status
        status_data = await status()
        return get_export_system().export_status_report(status_data)
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# File Watcher
# ──────────────────────────────────────────────────────────────

@router.get("/watcher")
async def watcher_status():
    try:
        from ald01.core.file_watcher import get_file_watcher
        fw = get_file_watcher()
        return {
            "stats": fw.get_stats(),
            "watched": fw.get_watched(),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/watcher/events")
async def watcher_events():
    try:
        from ald01.core.file_watcher import get_file_watcher
        return {"events": get_file_watcher().get_events(50)}
    except Exception as e:
        return {"events": [], "error": str(e)}


@router.post("/watcher/watch")
async def add_watch(request: Request):
    body = await request.json()
    try:
        from ald01.core.file_watcher import get_file_watcher
        result = get_file_watcher().watch(
            directory=body.get("directory", ""),
            label=body.get("label", ""),
        )
        return {"success": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Session Manager
# ──────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions():
    try:
        from ald01.core.session_manager import get_session_manager
        return {"sessions": get_session_manager().list_sessions()}
    except Exception as e:
        return {"sessions": [], "error": str(e)}


@router.get("/preferences")
async def get_preferences():
    try:
        from ald01.core.session_manager import get_session_manager
        return get_session_manager().get_preferences()
    except Exception as e:
        return {"error": str(e)}


@router.post("/preferences")
async def update_preferences(request: Request):
    body = await request.json()
    try:
        from ald01.core.session_manager import get_session_manager
        get_session_manager().update_preferences(body)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates():
    try:
        from ald01.core.template_engine import get_template_engine
        return {"templates": get_template_engine().list_templates()}
    except Exception as e:
        return {"templates": [], "error": str(e)}


@router.post("/templates/render")
async def render_template(request: Request):
    body = await request.json()
    try:
        from ald01.core.template_engine import get_template_engine
        return get_template_engine().render(
            template_id=body.get("template_id", ""),
            context=body.get("context", {}),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/templates/scaffold")
async def scaffold_project(request: Request):
    body = await request.json()
    try:
        from ald01.core.template_engine import get_template_engine
        return get_template_engine().scaffold_project(
            project_type=body.get("type", "python"),
            variables=body.get("variables", {}),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/prompts/stats")
async def prompt_stats():
    try:
        from ald01.core.prompt_library import get_prompt_library
        return get_prompt_library().get_stats()
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# Pipeline Manager
# ──────────────────────────────────────────────────────────────

@router.get("/pipelines")
async def list_pipelines():
    try:
        from ald01.core.pipeline import get_pipeline_manager
        return {"pipelines": get_pipeline_manager().list_pipelines()}
    except Exception as e:
        return {"pipelines": [], "error": str(e)}


@router.post("/pipelines")
async def create_pipeline(request: Request):
    body = await request.json()
    try:
        from ald01.core.pipeline import get_pipeline_manager
        return get_pipeline_manager().create_pipeline(
            pipeline_id=body.get("id", ""),
            name=body.get("name", ""),
            description=body.get("description", ""),
            steps=body.get("steps", []),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, request: Request):
    body = await request.json()
    try:
        from ald01.core.pipeline import get_pipeline_manager
        return await get_pipeline_manager().run(
            pipeline_id, context=body.get("context"),
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    try:
        from ald01.core.pipeline import get_pipeline_manager
        return {"success": get_pipeline_manager().delete_pipeline(pipeline_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/pipelines/templates")
async def list_pipeline_templates():
    try:
        from ald01.core.pipeline import get_pipeline_manager
        return {"templates": get_pipeline_manager().list_templates()}
    except Exception as e:
        return {"templates": [], "error": str(e)}


@router.post("/pipelines/from-template/{template_id}")
async def create_pipeline_from_template(template_id: str):
    try:
        from ald01.core.pipeline import get_pipeline_manager
        return get_pipeline_manager().create_from_template(template_id)
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/pipelines/stats")
async def pipeline_stats():
    try:
        from ald01.core.pipeline import get_pipeline_manager
        return get_pipeline_manager().get_stats()
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# Context Manager
# ──────────────────────────────────────────────────────────────

@router.get("/context/stats")
async def context_stats():
    try:
        from ald01.core.context_manager import get_context_manager
        return get_context_manager().get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/context/inject")
async def inject_context(request: Request):
    body = await request.json()
    try:
        from ald01.core.context_manager import get_context_manager
        cm = get_context_manager()
        cm.injector.set_injection(body.get("key", ""), body.get("content", ""))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/context/injections")
async def list_injections():
    try:
        from ald01.core.context_manager import get_context_manager
        return {"injections": get_context_manager().injector.list_injections()}
    except Exception as e:
        return {"injections": {}, "error": str(e)}


@router.get("/context/memory")
async def list_memories():
    try:
        from ald01.core.context_manager import get_context_manager
        return {"memories": get_context_manager().memory.list_all()}
    except Exception as e:
        return {"memories": [], "error": str(e)}


@router.post("/context/memory")
async def add_memory(request: Request):
    body = await request.json()
    try:
        from ald01.core.context_manager import get_context_manager
        get_context_manager().memory.remember(
            key=body.get("key", ""),
            value=body.get("value", ""),
            category=body.get("category", "general"),
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/context/memory/search")
async def search_memories(q: str = ""):
    try:
        from ald01.core.context_manager import get_context_manager
        return {"results": get_context_manager().memory.search(q)}
    except Exception as e:
        return {"results": [], "error": str(e)}
