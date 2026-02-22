"""
ALD-01 Enhanced Dashboard API v2
Additional REST endpoints for all new systems:
Chat Engine, Skills, MCP, Integrations, Revert, Database Overview.
"""

import os
import time
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse

logger = logging.getLogger("ald01.dashboard.api_v2")

router = APIRouter(prefix="/api/v2", tags=["dashboard-v2"])


# ──────────────────────────────────────────────────────────────
# Chat Engine (AGI Chat)
# ──────────────────────────────────────────────────────────────

@router.get("/chat/conversations")
async def list_chat_conversations():
    from ald01.core.chat_engine import get_chat_engine
    return get_chat_engine().list_conversations()


@router.post("/chat/new")
async def new_chat_conversation(request: Request):
    body = await request.json()
    from ald01.core.chat_engine import get_chat_engine
    conv = get_chat_engine().new_conversation(
        title=body.get("title", ""),
        agent=body.get("agent", "general"),
    )
    return conv.to_dict()


@router.get("/chat/conversations/{conv_id}/messages")
async def get_chat_messages(conv_id: str):
    from ald01.core.chat_engine import get_chat_engine
    return get_chat_engine().get_messages(conv_id)


@router.post("/chat/send")
async def send_chat_message(request: Request):
    body = await request.json()
    content = body.get("content", "")
    conv_id = body.get("conversation_id")
    agent = body.get("agent", "")
    if not content:
        raise HTTPException(400, "Missing content")
    from ald01.core.chat_engine import get_chat_engine
    msg = await get_chat_engine().send_message(content, conv_id, agent)
    return msg.to_dict()


@router.delete("/chat/conversations/{conv_id}")
async def delete_chat(conv_id: str):
    from ald01.core.chat_engine import get_chat_engine
    return {"success": get_chat_engine().delete_conversation(conv_id)}


@router.post("/chat/conversations/{conv_id}/archive")
async def archive_chat(conv_id: str):
    from ald01.core.chat_engine import get_chat_engine
    return {"success": get_chat_engine().archive_conversation(conv_id)}


@router.post("/chat/conversations/{conv_id}/pin")
async def pin_chat(conv_id: str):
    from ald01.core.chat_engine import get_chat_engine
    return {"success": get_chat_engine().pin_conversation(conv_id, True)}


@router.get("/chat/search")
async def search_chats(q: str = ""):
    from ald01.core.chat_engine import get_chat_engine
    return get_chat_engine().search_conversations(q)


@router.get("/chat/stats")
async def chat_stats():
    from ald01.core.chat_engine import get_chat_engine
    return get_chat_engine().get_stats()


@router.post("/chat/voice/toggle")
async def toggle_voice(request: Request):
    body = await request.json()
    from ald01.core.chat_engine import get_chat_engine
    engine = get_chat_engine()
    engine.voice_enabled = body.get("enabled", False)
    return {"voice_enabled": engine.voice_enabled}


# ──────────────────────────────────────────────────────────────
# Skills
# ──────────────────────────────────────────────────────────────

@router.get("/skills/available")
async def available_skills():
    from ald01.core.skill_manager import get_skill_manager
    return get_skill_manager().list_available()


@router.get("/skills/installed")
async def installed_skills():
    from ald01.core.skill_manager import get_skill_manager
    return get_skill_manager().list_installed()


@router.post("/skills/{skill_id}/install")
async def install_skill(skill_id: str):
    from ald01.core.skill_manager import get_skill_manager
    return get_skill_manager().install_skill(skill_id)


@router.post("/skills/{skill_id}/uninstall")
async def uninstall_skill(skill_id: str):
    from ald01.core.skill_manager import get_skill_manager
    return {"success": get_skill_manager().uninstall_skill(skill_id)}


@router.post("/skills/{skill_id}/enable")
async def enable_skill(skill_id: str):
    from ald01.core.skill_manager import get_skill_manager
    return {"success": get_skill_manager().enable_skill(skill_id)}


@router.post("/skills/{skill_id}/disable")
async def disable_skill(skill_id: str):
    from ald01.core.skill_manager import get_skill_manager
    return {"success": get_skill_manager().disable_skill(skill_id)}


@router.get("/skills/stats")
async def skill_stats():
    from ald01.core.skill_manager import get_skill_manager
    return get_skill_manager().get_stats()


@router.get("/skills/recommend")
async def recommend_skills(q: str = ""):
    from ald01.core.skill_manager import get_skill_manager
    return get_skill_manager().auto_recommend(q)


# ──────────────────────────────────────────────────────────────
# MCP Servers
# ──────────────────────────────────────────────────────────────

@router.get("/mcp/available")
async def list_mcp_available():
    from ald01.core.mcp_manager import get_mcp_manager
    return get_mcp_manager().list_available()


@router.get("/mcp/installed")
async def list_mcp_installed():
    from ald01.core.mcp_manager import get_mcp_manager
    return get_mcp_manager().list_installed()


@router.post("/mcp/{server_id}/install")
async def install_mcp(server_id: str):
    from ald01.core.mcp_manager import get_mcp_manager
    return await get_mcp_manager().install_server(server_id)


@router.post("/mcp/{server_id}/uninstall")
async def uninstall_mcp(server_id: str):
    from ald01.core.mcp_manager import get_mcp_manager
    return {"success": get_mcp_manager().uninstall_server(server_id)}


@router.post("/mcp/{server_id}/enable")
async def enable_mcp(server_id: str):
    from ald01.core.mcp_manager import get_mcp_manager
    return {"success": get_mcp_manager().enable_server(server_id)}


@router.post("/mcp/{server_id}/disable")
async def disable_mcp(server_id: str):
    from ald01.core.mcp_manager import get_mcp_manager
    return {"success": get_mcp_manager().disable_server(server_id)}


@router.get("/mcp/config")
async def get_mcp_config():
    from ald01.core.mcp_manager import get_mcp_manager
    return get_mcp_manager().get_config_for_client()


@router.get("/mcp/stats")
async def mcp_stats():
    from ald01.core.mcp_manager import get_mcp_manager
    return get_mcp_manager().get_stats()


# ──────────────────────────────────────────────────────────────
# External Tool Integrations
# ──────────────────────────────────────────────────────────────

@router.get("/integrations/scan")
async def scan_integrations():
    from ald01.core.integrations import get_integration_manager
    return get_integration_manager().scan_tools()


@router.get("/integrations/tools")
async def list_integrations():
    from ald01.core.integrations import get_integration_manager
    return get_integration_manager().get_detected_tools()


@router.get("/integrations/categories")
async def integration_categories():
    from ald01.core.integrations import get_integration_manager
    return get_integration_manager().get_tools_by_category()


@router.post("/integrations/{tool_name}/invoke")
async def invoke_integration(tool_name: str, request: Request):
    body = await request.json()
    from ald01.core.integrations import get_integration_manager
    return await get_integration_manager().invoke_tool(
        tool_name, body.get("args", []), body.get("timeout", 30)
    )


# ──────────────────────────────────────────────────────────────
# Self-Revert / Snapshots
# ──────────────────────────────────────────────────────────────

@router.get("/revert/snapshots")
async def list_snapshots():
    from ald01.core.revert import get_revert_manager
    return get_revert_manager().list_snapshots()


@router.post("/revert/snapshot")
async def create_snapshot(request: Request):
    body = await request.json()
    from ald01.core.revert import get_revert_manager
    name = get_revert_manager().create_snapshot(body.get("label", ""))
    return {"success": True, "snapshot": name}


@router.post("/revert/restore/{snap_name}")
async def restore_snapshot(snap_name: str):
    from ald01.core.revert import get_revert_manager
    return get_revert_manager().revert_to_snapshot(snap_name)


@router.post("/revert/config-reset")
async def reset_config():
    from ald01.core.revert import get_revert_manager
    return get_revert_manager().revert_config_only()


@router.post("/revert/doctor-fix")
async def doctor_fix():
    from ald01.core.revert import get_revert_manager
    return get_revert_manager().doctor_fix()


@router.delete("/revert/snapshots/{snap_name}")
async def delete_snapshot(snap_name: str):
    from ald01.core.revert import get_revert_manager
    return {"success": get_revert_manager().delete_snapshot(snap_name)}


# ──────────────────────────────────────────────────────────────
# Database Overview
# ──────────────────────────────────────────────────────────────

@router.get("/database/overview")
async def database_overview():
    """Get database overview with table info, sizes, and row counts."""
    import sqlite3
    from ald01 import MEMORY_DIR

    db_path = os.path.join(MEMORY_DIR, "ald01.db")
    if not os.path.exists(db_path):
        return {"exists": False, "tables": []}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = []
        total_rows = 0

        for (table_name,) in cursor.fetchall():
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            row_count = cursor.fetchone()[0]
            total_rows += row_count

            # Get columns
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = [
                {"name": col[1], "type": col[2], "nullable": not col[3], "pk": bool(col[5])}
                for col in cursor.fetchall()
            ]

            tables.append({
                "name": table_name,
                "row_count": row_count,
                "columns": columns,
                "column_count": len(columns),
            })

        # DB file size
        db_size = os.path.getsize(db_path)

        # Integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]

        conn.close()

        return {
            "exists": True,
            "path": db_path,
            "size_kb": round(db_size / 1024, 1),
            "size_mb": round(db_size / (1024 * 1024), 2),
            "table_count": len(tables),
            "total_rows": total_rows,
            "integrity": integrity,
            "tables": tables,
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}


@router.get("/database/query")
async def database_query(sql: str = ""):
    """Run a read-only SQL query on the database."""
    if not sql:
        raise HTTPException(400, "Missing sql parameter")

    # Safety: only allow SELECT
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("PRAGMA"):
        raise HTTPException(400, "Only SELECT and PRAGMA queries are allowed")

    import sqlite3
    from ald01 import MEMORY_DIR

    db_path = os.path.join(MEMORY_DIR, "ald01.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()[:100]]
        conn.close()
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(400, str(e))


# ──────────────────────────────────────────────────────────────
# Settings — Test subpage
# ──────────────────────────────────────────────────────────────

@router.get("/settings/test")
async def run_settings_test():
    """Run diagnostics test from settings."""
    results = {
        "timestamp": time.time(),
        "tests": [],
    }

    # Test 1: Config load
    try:
        from ald01.config import get_config
        config = get_config()
        results["tests"].append({
            "name": "Config Load",
            "status": "pass",
            "detail": f"Brain power: {config.brain_power}",
        })
    except Exception as e:
        results["tests"].append({"name": "Config Load", "status": "fail", "detail": str(e)})

    # Test 2: Memory
    try:
        from ald01.core.memory import get_memory
        mem = get_memory()
        stats = mem.get_stats()
        results["tests"].append({
            "name": "Memory System",
            "status": "pass",
            "detail": f"Stats: {stats}",
        })
    except Exception as e:
        results["tests"].append({"name": "Memory System", "status": "fail", "detail": str(e)})

    # Test 3: Brain
    try:
        from ald01.core.brain import get_brain
        brain = get_brain()
        brain_stats = brain.get_stats()
        results["tests"].append({
            "name": "AGI Brain",
            "status": "pass",
            "detail": f"Nodes: {brain_stats['total_nodes']}, Skills: {brain_stats['skills_count']}",
        })
    except Exception as e:
        results["tests"].append({"name": "AGI Brain", "status": "fail", "detail": str(e)})

    # Test 4: Scheduler
    try:
        from ald01.core.scheduler import get_scheduler
        sched = get_scheduler()
        jobs = sched.list_jobs()
        results["tests"].append({
            "name": "Scheduler",
            "status": "pass",
            "detail": f"Jobs: {len(jobs)}",
        })
    except Exception as e:
        results["tests"].append({"name": "Scheduler", "status": "fail", "detail": str(e)})

    # Test 5: Self-Heal
    try:
        from ald01.core.self_heal import get_self_healing_engine
        engine = get_self_healing_engine()
        health = engine.run_health_check()
        results["tests"].append({
            "name": "Self-Healing",
            "status": "pass",
            "detail": f"Checks: {len(health.get('checks', []))}",
        })
    except Exception as e:
        results["tests"].append({"name": "Self-Healing", "status": "fail", "detail": str(e)})

    # Test 6: Data Manager
    try:
        from ald01.core.data_manager import get_data_manager
        dm = get_data_manager()
        storage = dm.get_storage_info()
        results["tests"].append({
            "name": "Data Manager",
            "status": "pass",
            "detail": f"Total: {storage.get('total_size_mb', 0)} MB",
        })
    except Exception as e:
        results["tests"].append({"name": "Data Manager", "status": "fail", "detail": str(e)})

    # Test 7: Localization
    try:
        from ald01.core.localization import get_localization
        loc = get_localization()
        results["tests"].append({
            "name": "Localization",
            "status": "pass",
            "detail": f"Language: {loc.current_language}",
        })
    except Exception as e:
        results["tests"].append({"name": "Localization", "status": "fail", "detail": str(e)})

    # Test 8: Notifications
    try:
        from ald01.core.notifications import get_notification_manager
        nm = get_notification_manager()
        results["tests"].append({
            "name": "Notifications",
            "status": "pass",
            "detail": f"History: {len(nm.get_history())} events",
        })
    except Exception as e:
        results["tests"].append({"name": "Notifications", "status": "fail", "detail": str(e)})

    # Summary
    passed = sum(1 for t in results["tests"] if t["status"] == "pass")
    total = len(results["tests"])
    results["summary"] = {
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "health": "healthy" if passed == total else "degraded",
    }

    return results


@router.get("/settings/all")
async def get_all_settings():
    """Get comprehensive settings overview."""
    settings = {}

    try:
        from ald01.config import get_config
        config = get_config()
        settings["brain_power"] = config.brain_power
    except Exception:
        settings["brain_power"] = 5

    try:
        from ald01.core.localization import get_localization
        settings["language"] = get_localization().current_language
    except Exception:
        settings["language"] = "en"

    try:
        from ald01.core.autostart import get_autostart_manager
        settings["autostart"] = get_autostart_manager().is_enabled()
    except Exception:
        settings["autostart"] = False

    try:
        from ald01.core.chat_engine import get_chat_engine
        settings["voice_enabled"] = get_chat_engine().voice_enabled
    except Exception:
        settings["voice_enabled"] = False

    try:
        from ald01.core.multi_model import get_multi_model
        mm = get_multi_model()
        settings["multi_model"] = mm.get_config()
    except Exception:
        settings["multi_model"] = {}

    try:
        from ald01.core.data_manager import get_data_manager
        settings["storage"] = get_data_manager().get_storage_info()
    except Exception:
        settings["storage"] = {}

    return settings
