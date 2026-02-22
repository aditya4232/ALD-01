"""
ALD-01 Dashboard Server
FastAPI-based web dashboard with WebSocket for real-time activity visualization.
Includes sandbox editor, file browser, system monitor, and agent activity viewer.
"""

import os
import json
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ald01.config import get_config, get_brain_power_preset, BRAIN_POWER_PRESETS
from ald01.core.orchestrator import get_orchestrator
from ald01.core.memory import get_memory
from ald01.core.events import get_event_bus, EventType
from ald01.core.tools import get_tool_executor
from ald01.providers.manager import get_provider_manager
from ald01.providers.openai_compat import list_free_providers
from ald01.doctor.diagnostics import DoctorDiagnostics

logger = logging.getLogger("ald01.dashboard")

app = FastAPI(title="ALD-01 Dashboard", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# API Routes
# ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the main dashboard HTML."""
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>ALD-01 Dashboard</h1><p>Static files not found. Rebuild.</p>")


@app.get("/api/status")
async def get_status():
    """Get system status."""
    orch = get_orchestrator()
    return JSONResponse(orch.get_status())


@app.get("/api/agents")
async def get_agents():
    """Get all agent info."""
    orch = get_orchestrator()
    return JSONResponse(orch.get_agents())


@app.get("/api/providers")
async def get_providers():
    """Get provider statuses."""
    mgr = get_provider_manager()
    return JSONResponse(mgr.get_stats())


@app.post("/api/providers/test")
async def test_providers():
    """Test all provider connections."""
    mgr = get_provider_manager()
    results = await mgr.test_all()
    return JSONResponse({name: s.to_dict() for name, s in results.items()})


@app.get("/api/providers/free")
async def get_free_providers():
    """List available free providers."""
    return JSONResponse(list_free_providers())


@app.get("/api/brain-power")
async def get_brain_power():
    """Get brain power presets."""
    config = get_config()
    return JSONResponse({
        "current": config.brain_power,
        "presets": BRAIN_POWER_PRESETS,
    })


@app.post("/api/brain-power/{level}")
async def set_brain_power(level: int):
    """Set brain power level."""
    config = get_config()
    config.brain_power = level
    config.save()
    return JSONResponse({"level": level, "preset": get_brain_power_preset(level)})


# ──────────────────────────────────────────────────────────────
# Chat API
# ──────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    """Send a chat message and get a response."""
    body = await request.json()
    query = body.get("query", "")
    agent = body.get("agent", None)
    conversation_id = body.get("conversation_id", None)

    if not query:
        raise HTTPException(400, "Missing 'query'")

    orch = get_orchestrator()
    response = await orch.process_query(query, agent_name=agent, conversation_id=conversation_id)
    return JSONResponse(response.to_dict())


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """Stream a chat response."""
    body = await request.json()
    query = body.get("query", "")
    agent = body.get("agent", None)
    conversation_id = body.get("conversation_id", None)

    if not query:
        raise HTTPException(400, "Missing 'query'")

    orch = get_orchestrator()

    async def stream_generator():
        async for chunk in orch.stream_query(query, agent_name=agent, conversation_id=conversation_id):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


# ──────────────────────────────────────────────────────────────
# Conversations API
# ──────────────────────────────────────────────────────────────

@app.get("/api/conversations")
async def list_conversations():
    """List conversations."""
    mem = get_memory()
    return JSONResponse(mem.list_conversations())


@app.get("/api/conversations/{conv_id}/messages")
async def get_messages(conv_id: str):
    """Get messages for a conversation."""
    mem = get_memory()
    messages = mem.get_messages(conv_id, limit=100)
    return JSONResponse([m.to_dict() for m in messages])


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    mem = get_memory()
    mem.delete_conversation(conv_id)
    return JSONResponse({"deleted": conv_id})


# ──────────────────────────────────────────────────────────────
# Tools API (File Browser, Terminal, System)
# ──────────────────────────────────────────────────────────────

@app.post("/api/tools/execute")
async def execute_tool(request: Request):
    """Execute a tool."""
    body = await request.json()
    tool_name = body.get("tool", "")
    params = body.get("params", {})
    if not tool_name:
        raise HTTPException(400, "Missing 'tool'")

    executor = get_tool_executor()
    result = await executor.execute(tool_name, params)
    return JSONResponse(result.to_dict())


@app.get("/api/tools")
async def list_tools():
    """List available tools."""
    executor = get_tool_executor()
    return JSONResponse(executor.get_available_tools())


@app.post("/api/files/read")
async def read_file(request: Request):
    """Read a file (for sandbox editor)."""
    body = await request.json()
    path = body.get("path", "")
    executor = get_tool_executor()
    result = await executor.execute("file_read", {"path": path})
    return JSONResponse(result.to_dict())


@app.post("/api/files/write")
async def write_file(request: Request):
    """Write a file (from sandbox editor)."""
    body = await request.json()
    path = body.get("path", "")
    content = body.get("content", "")
    executor = get_tool_executor()
    result = await executor.execute("file_write", {"path": path, "content": content})
    return JSONResponse(result.to_dict())


@app.post("/api/files/list")
async def list_files(request: Request):
    """List files in a directory."""
    body = await request.json()
    path = body.get("path", os.path.expanduser("~"))
    executor = get_tool_executor()
    result = await executor.execute("file_list", {"path": path, "show_hidden": body.get("show_hidden", False)})
    return JSONResponse(result.to_dict())


@app.post("/api/sandbox/run")
async def sandbox_run(request: Request):
    """Execute code in sandbox."""
    body = await request.json()
    code = body.get("code", "")
    executor = get_tool_executor()
    result = await executor.execute("code_execute", {"code": code, "timeout": 30})
    return JSONResponse(result.to_dict())


@app.post("/api/terminal/run")
async def terminal_run(request: Request):
    """Execute command in terminal."""
    body = await request.json()
    command = body.get("command", "")
    cwd = body.get("cwd", None)
    executor = get_tool_executor()
    result = await executor.execute("terminal", {"command": command, "cwd": cwd, "timeout": 30})
    return JSONResponse(result.to_dict())


@app.get("/api/system/info")
async def system_info():
    """Get system information."""
    executor = get_tool_executor()
    result = await executor.execute("system_info")
    return JSONResponse(result.to_dict())


@app.get("/api/system/processes")
async def system_processes():
    """Get running processes."""
    executor = get_tool_executor()
    result = await executor.execute("process_list", {"limit": 30})
    return JSONResponse(result.to_dict())


# ──────────────────────────────────────────────────────────────
# Doctor API
# ──────────────────────────────────────────────────────────────

@app.get("/api/doctor")
async def run_doctor():
    """Run doctor diagnostics."""
    doctor = DoctorDiagnostics()
    await doctor.run_all()
    return JSONResponse(doctor.get_summary())


# ──────────────────────────────────────────────────────────────
# Activity & Decision Logs
# ──────────────────────────────────────────────────────────────

@app.get("/api/activity")
async def get_activity():
    """Get recent activity log."""
    orch = get_orchestrator()
    return JSONResponse(orch.get_activity_log())


@app.get("/api/decisions")
async def get_decisions():
    """Get recent AI decisions."""
    mem = get_memory()
    return JSONResponse(mem.get_decisions(limit=50))


@app.get("/api/thinking")
async def get_thinking():
    """Get thinking log."""
    mem = get_memory()
    return JSONResponse(mem.get_thinking_log(limit=50))


@app.get("/api/memory/stats")
async def memory_stats():
    """Get memory statistics."""
    mem = get_memory()
    return JSONResponse(mem.get_stats())


# ──────────────────────────────────────────────────────────────
# Export API (for sandbox editor)
# ──────────────────────────────────────────────────────────────

@app.post("/api/export")
async def export_content(request: Request):
    """Export content as a downloadable file."""
    body = await request.json()
    content = body.get("content", "")
    filename = body.get("filename", "export.txt")

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=f"_{filename}", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name

    return FileResponse(tmp_path, filename=filename, media_type="application/octet-stream")


# ──────────────────────────────────────────────────────────────
# WebSocket (Real-time Visualizer)
# ──────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket for real-time event streaming to dashboard visualizer."""
    await ws.accept()
    event_bus = get_event_bus()
    queue = event_bus.subscribe()

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                await ws.send_json(event.to_dict())
            except asyncio.TimeoutError:
                # Send heartbeat
                await ws.send_json({"type": "heartbeat", "timestamp": time.time()})
    except WebSocketDisconnect:
        event_bus.unsubscribe(queue)
    except Exception as e:
        event_bus.unsubscribe(queue)
        logger.debug(f"WebSocket closed: {e}")


# ──────────────────────────────────────────────────────────────
# Server Launcher
# ──────────────────────────────────────────────────────────────

def run_dashboard(host: str = "127.0.0.1", port: int = 7860):
    """Start the dashboard server."""
    config = get_config()
    host = host or config.get("dashboard", "host", default="127.0.0.1")
    port = port or config.get("dashboard", "port", default=7860)

    logger.info(f"Starting ALD-01 Dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


async def run_dashboard_async(host: str = "127.0.0.1", port: int = 7860):
    """Start dashboard asynchronously."""
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
