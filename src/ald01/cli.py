"""
ALD-01 CLI
Command-line interface for the ALD-01 AI agent system.
"""

import os
import sys
import asyncio
import logging
import time
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from ald01 import __version__, __project__, __description__
from ald01.config import get_config, BRAIN_POWER_PRESETS

console = Console()

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _run_async(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _print_banner():
    """Print the ALD-01 banner."""
    banner = """
    ╔═══════════════════════════════════════╗
    ║         █████╗ ██╗     ██████╗        ║
    ║        ██╔══██╗██║     ██╔══██╗       ║
    ║        ███████║██║     ██║  ██║       ║
    ║        ██╔══██║██║     ██║  ██║       ║
    ║        ██║  ██║███████╗██████╔╝       ║
    ║        ╚═╝  ╚═╝╚══════╝╚═════╝        ║
    ║    Advanced Local Desktop Intelligence ║
    ║             v{version}                    ║
    ╚═══════════════════════════════════════╝
    """.format(version=__version__)
    console.print(Text(banner, style="bold cyan"))


# ──────────────────────────────────────────────────────────────
# Main CLI Group
# ──────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="ald-01")
@click.pass_context
def main(ctx):
    """ALD-01 — Advanced Local Desktop Intelligence"""
    if ctx.invoked_subcommand is None:
        _print_banner()
        console.print("  [dim]Run [bold]ald-01 --help[/bold] for all commands[/dim]\n")
        console.print("  Quick start:")
        console.print("    [cyan]ald-01 doctor[/cyan]    — Run diagnostics")
        console.print("    [cyan]ald-01 chat[/cyan]      — Start chatting")
        console.print("    [cyan]ald-01 dashboard[/cyan]  — Launch web UI")
        console.print("    [cyan]ald-01 status[/cyan]    — System status")
        console.print()


# ──────────────────────────────────────────────────────────────
# Chat Command
# ──────────────────────────────────────────────────────────────

@main.command()
@click.argument("query", nargs=-1, required=False)
@click.option("--agent", "-a", default=None, help="Force a specific agent (code_gen, debug, review, security, general)")
@click.option("--stream/--no-stream", default=True, help="Stream the response")
@click.option("--voice/--no-voice", default=False, help="Speak the response")
def chat(query, agent, stream, voice):
    """Chat with ALD-01. Use interactively or pass a query."""
    query_text = " ".join(query) if query else None

    if query_text:
        # One-shot mode
        _run_async(_single_chat(query_text, agent, stream, voice))
    else:
        # Interactive mode
        _run_async(_interactive_chat(agent, stream, voice))


async def _single_chat(query: str, agent: Optional[str], stream: bool, voice: bool):
    """Process a single chat query."""
    from ald01.core.orchestrator import get_orchestrator

    orch = get_orchestrator()
    await orch.initialize()

    if stream:
        full_response = ""
        with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            pass

        console.print()
        async for chunk in orch.stream_query(query, agent_name=agent):
            console.print(chunk, end="")
            full_response += chunk
        console.print("\n")

        if voice and full_response:
            from ald01.services.voice import get_voice_service
            vs = get_voice_service()
            await vs.initialize()
            await vs.speak(full_response)
    else:
        with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            response = await orch.process_query(query, agent_name=agent)

        console.print()
        console.print(Panel(
            Markdown(response.content),
            title=f"[cyan]ALD-01 ({response.agent_name})[/cyan]",
            subtitle=f"[dim]{response.model} via {response.provider} ({response.latency_ms:.0f}ms)[/dim]",
            border_style="dim",
        ))

        if voice:
            from ald01.services.voice import get_voice_service
            vs = get_voice_service()
            await vs.initialize()
            await vs.speak(response.content)


async def _interactive_chat(agent: Optional[str], stream: bool, voice: bool):
    """Interactive chat loop."""
    from ald01.core.orchestrator import get_orchestrator

    _print_banner()
    console.print("[dim]Type your message. Commands: /exit, /clear, /agent <name>, /voice on|off[/dim]\n")

    orch = get_orchestrator()
    await orch.initialize()

    conversation_id = None
    voice_enabled = voice

    while True:
        try:
            user_input = console.input("[bold green]You > [/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in ["/exit", "/quit", "/q"]:
                console.print("[dim]Goodbye![/dim]")
                break
            elif cmd == "/clear":
                console.clear()
                _print_banner()
                conversation_id = None
                console.print("[dim]Conversation cleared.[/dim]")
                continue
            elif cmd.startswith("/agent"):
                parts = cmd.split()
                if len(parts) > 1:
                    agent = parts[1]
                    console.print(f"[dim]Agent set to: {agent}[/dim]")
                else:
                    console.print("[dim]Agents: code_gen, debug, review, security, general[/dim]")
                continue
            elif cmd.startswith("/voice"):
                parts = cmd.split()
                if len(parts) > 1 and parts[1] == "on":
                    voice_enabled = True
                    console.print("[dim]Voice: ON[/dim]")
                else:
                    voice_enabled = False
                    console.print("[dim]Voice: OFF[/dim]")
                continue
            elif cmd == "/status":
                status = orch.get_status()
                console.print(Panel(
                    f"Uptime: {status['uptime_human']}\n"
                    f"Brain Power: {status['brain_power']} ({status['brain_power_name']})\n"
                    f"Requests: {status['total_requests']}\n"
                    f"Providers: {status['providers']['online_providers']}/{status['providers']['total_providers']}",
                    title="[cyan]Status[/cyan]",
                ))
                continue

        # Process query
        try:
            if stream:
                full_response = ""
                console.print()
                console.print("[bold cyan]ALD-01 > [/bold cyan]", end="")
                async for chunk in orch.stream_query(user_input, agent_name=agent, conversation_id=conversation_id):
                    console.print(chunk, end="")
                    full_response += chunk
                console.print("\n")

                if voice_enabled and full_response:
                    from ald01.services.voice import get_voice_service
                    vs = get_voice_service()
                    await vs.initialize()
                    await vs.speak(full_response[:500])
            else:
                with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                    response = await orch.process_query(user_input, agent_name=agent, conversation_id=conversation_id)

                console.print()
                console.print(Panel(
                    Markdown(response.content),
                    title=f"[cyan]ALD-01 ({response.agent_name})[/cyan]",
                    subtitle=f"[dim]{response.model} — {response.latency_ms:.0f}ms[/dim]",
                    border_style="dim",
                ))

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")


# ──────────────────────────────────────────────────────────────
# Ask Command (shortcut for single query)
# ──────────────────────────────────────────────────────────────

@main.command()
@click.argument("query", nargs=-1, required=True)
def ask(query):
    """Quick one-shot question. Example: ald-01 ask 'How do I sort a list in Python?'"""
    _run_async(_single_chat(" ".join(query), None, True, False))


# ──────────────────────────────────────────────────────────────
# Dashboard Command
# ──────────────────────────────────────────────────────────────

@main.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind")
@click.option("--port", "-p", default=7860, help="Port to bind")
@click.option("--open/--no-open", default=True, help="Open browser automatically")
def dashboard(host, port, open):
    """Launch the ALD-01 web dashboard."""
    from ald01.dashboard.server import run_dashboard

    _print_banner()
    console.print(f"[cyan]Dashboard starting at [bold]http://{host}:{port}[/bold][/cyan]")

    if open:
        import webbrowser
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    run_dashboard(host, port)


# ──────────────────────────────────────────────────────────────
# Status Command
# ──────────────────────────────────────────────────────────────

@main.command()
def status():
    """Show system status."""
    async def _status():
        from ald01.core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        await orch.initialize()
        s = orch.get_status()

        _print_banner()

        # System table
        table = Table(title="System Status", show_header=True, header_style="bold cyan")
        table.add_column("Component", style="bold")
        table.add_column("Status")
        table.add_column("Details")

        table.add_row("System", "[green]Running[/green]" if s["status"] == "running" else "[red]Stopped[/red]",
                      f"Uptime: {s['uptime_human']}")
        table.add_row("Brain Power", f"Level {s['brain_power']}", s["brain_power_name"])
        table.add_row("Requests", str(s["total_requests"]), "total processed")
        table.add_row("Providers",
                      f"[green]{s['providers']['online_providers']}[/green]/{s['providers']['total_providers']}",
                      "online")
        table.add_row("Memory", f"{s['memory']['messages']} messages",
                      f"{s['memory']['db_size_mb']} MB")
        table.add_row("Conversations", str(s['memory']['conversations']), "stored")

        console.print(table)

        # Agents table
        agent_table = Table(title="Agents", show_header=True, header_style="bold magenta")
        agent_table.add_column("Agent")
        agent_table.add_column("Status")
        agent_table.add_column("Tasks")
        for name, agent in s["agents"].items():
            status_str = "[green]Enabled[/green]" if agent["enabled"] else "[red]Disabled[/red]"
            agent_table.add_row(agent["display_name"], status_str, str(agent["tasks_completed"]))
        console.print(agent_table)

    _run_async(_status())


# ──────────────────────────────────────────────────────────────
# Doctor Command
# ──────────────────────────────────────────────────────────────

@main.command()
def doctor():
    """Run comprehensive diagnostics."""
    async def _doctor():
        _print_banner()
        console.print("[cyan]Running diagnostics...[/cyan]\n")

        from ald01.doctor.diagnostics import DoctorDiagnostics
        doc = DoctorDiagnostics()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Checking system health...", total=None)
            results = await doc.run_all()
            progress.update(task, completed=True)

        # Display results
        table = Table(title="Diagnostic Results", show_header=True, header_style="bold cyan")
        table.add_column("Check", style="bold", min_width=20)
        table.add_column("Status", justify="center", min_width=6)
        table.add_column("Details", min_width=40)

        for r in results:
            status_color = {"pass": "green", "warn": "yellow", "fail": "red"}.get(r.status, "white")
            table.add_row(
                r.name,
                f"[{status_color}]{r.icon}[/{status_color}]",
                r.message,
            )

        console.print(table)

        # Summary
        summary = doc.get_summary()
        console.print()
        if summary["healthy"]:
            console.print("[bold green]✓ All checks passed![/bold green]")
        else:
            console.print(f"[yellow]⚠ {summary['failed']} issue(s) found, {summary['fixable']} fixable[/yellow]")
        console.print(f"  Passed: {summary['passed']} | Warnings: {summary['warnings']} | Failed: {summary['failed']}")

    _run_async(_doctor())


# ──────────────────────────────────────────────────────────────
# Provider Commands
# ──────────────────────────────────────────────────────────────

@main.group()
def provider():
    """Manage AI providers."""
    pass


@provider.command("list")
def provider_list():
    """List all providers and their status."""
    async def _list():
        from ald01.providers.manager import get_provider_manager
        mgr = get_provider_manager()
        await mgr.initialize()
        statuses = await mgr.test_all()

        table = Table(title="AI Providers", show_header=True, header_style="bold cyan")
        table.add_column("Provider", style="bold")
        table.add_column("Status")
        table.add_column("Latency")
        table.add_column("Models")

        for name, status in statuses.items():
            online = "[green]● Online[/green]" if status.online else "[red]○ Offline[/red]"
            latency = f"{status.latency_ms:.0f}ms" if status.online else "-"
            models = ", ".join(status.models[:3]) + ("..." if len(status.models) > 3 else "") if status.models else "-"
            table.add_row(name, online, latency, models)

        console.print(table)

    _run_async(_list())


@provider.command("free")
def provider_free():
    """Show available free AI providers."""
    from ald01.providers.openai_compat import list_free_providers

    table = Table(title="Free AI Providers", show_header=True, header_style="bold green")
    table.add_column("Provider", style="bold")
    table.add_column("Model")
    table.add_column("Env Variable")
    table.add_column("Status")
    table.add_column("Description")

    for p in list_free_providers():
        if not p["free_tier"]:
            continue
        status = "[green]✓ Configured[/green]" if p["configured"] else "[dim]Not set[/dim]"
        table.add_row(p["name"], p["default_model"], p["env_key"], status, p["description"][:50])

    console.print(table)
    console.print("\n[dim]Set an API key: export <ENV_KEY>=<your-key>[/dim]")


@provider.command("add")
@click.argument("name")
@click.option("--url", "-u", help="API base URL")
@click.option("--key", "-k", help="API key")
@click.option("--model", "-m", default="auto", help="Default model")
def provider_add(name, url, key, model):
    """Add a provider. For free providers, just use the name (groq, cerebras, etc.)."""
    async def _add():
        from ald01.providers.manager import get_provider_manager
        from ald01.providers.openai_compat import FREE_PROVIDERS

        mgr = get_provider_manager()
        await mgr.initialize()

        if name in FREE_PROVIDERS:
            if not key:
                env_key = FREE_PROVIDERS[name].get("env_key", "")
                key_val = os.environ.get(env_key, "")
                if not key_val:
                    console.print(f"[yellow]Set API key: export {env_key}=<your-key>[/yellow]")
                    return
            else:
                key_val = key
            success = mgr.add_free_provider(name, key_val)
            if success:
                console.print(f"[green]✓ Added {FREE_PROVIDERS[name]['name']}[/green]")
        elif url:
            mgr.add_custom_provider(name, url, key or "", model)
            console.print(f"[green]✓ Added custom provider: {name}[/green]")
        else:
            console.print("[red]Unknown provider. Use --url for custom or one of: " +
                         ", ".join(FREE_PROVIDERS.keys()) + "[/red]")

    _run_async(_add())


# ──────────────────────────────────────────────────────────────
# Config Commands
# ──────────────────────────────────────────────────────────────

@main.group()
def config():
    """Manage configuration."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    cfg = get_config()
    import yaml
    console.print(Panel(yaml.dump(cfg._config, default_flow_style=False), title="Configuration"))


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a config value. Example: ald-01 config set brain_power 7"""
    cfg = get_config()
    keys = key.split(".")
    cfg.set(*keys, value=value)
    cfg.save()
    console.print(f"[green]✓ Set {key} = {value}[/green]")


@config.command("reset")
def config_reset():
    """Reset to default configuration."""
    cfg = get_config()
    cfg.reset()
    cfg.save()
    console.print("[green]✓ Configuration reset to defaults[/green]")


# ──────────────────────────────────────────────────────────────
# Voice Commands
# ──────────────────────────────────────────────────────────────

@main.group()
def voice():
    """Manage voice / TTS settings."""
    pass


@voice.command("test")
@click.argument("text", default="Hello! I am ALD-01, your personal AI assistant.")
def voice_test(text):
    """Test voice output."""
    async def _test():
        from ald01.services.voice import get_voice_service
        vs = get_voice_service()
        ok = await vs.initialize()
        if ok:
            console.print(f"[green]Engine: {vs.engine_name}[/green]")
            console.print(f"[cyan]Speaking...[/cyan]")
            await vs.speak(text)
        else:
            console.print("[yellow]No TTS engine available. Install: pip install edge-tts[/yellow]")

    _run_async(_test())


@voice.command("voices")
def voice_list():
    """List available voices."""
    async def _list():
        from ald01.services.voice import get_voice_service
        vs = get_voice_service()
        await vs.initialize()
        voices = await vs.list_voices()
        if voices:
            table = Table(title="Available Voices", header_style="bold cyan")
            table.add_column("ID")
            table.add_column("Name")
            table.add_column("Locale")
            for v in voices[:20]:
                table.add_row(v.get("id", ""), v.get("name", ""), v.get("locale", ""))
            console.print(table)
        else:
            console.print("[yellow]No voices found.[/yellow]")

    _run_async(_list())


if __name__ == "__main__":
    main()
