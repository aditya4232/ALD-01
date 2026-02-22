"""
ALD-01 Onboarding Wizard
Interactive first-time setup wizard for new users.
Handles provider setup, brain power configuration, voice selection, and API key management.
"""

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from ald01.config import get_config, BRAIN_POWER_PRESETS
from ald01.providers.openai_compat import FREE_PROVIDERS
from ald01.utils.hardware import detect_hardware, get_system_info_summary

logger = logging.getLogger("ald01.onboarding")
console = Console()


class OnboardingWizard:
    """Interactive first-time setup wizard."""

    def __init__(self):
        self._config = get_config()

    async def run(self) -> None:
        """Run the complete onboarding wizard."""
        console.clear()
        self._print_welcome()

        # Step 1: System Detection
        console.print("\n[bold cyan]Step 1/5: System Detection[/bold cyan]")
        console.print("[dim]Analyzing your hardware...[/dim]\n")
        hw = detect_hardware()
        self._display_hardware(hw)

        # Step 2: Brain Power
        console.print("\n[bold cyan]Step 2/5: Brain Power Level[/bold cyan]")
        recommended = hw.get("recommended_brain_power", 5)
        self._display_brain_presets()
        level = Prompt.ask(
            f"Choose brain power level (1-10)",
            default=str(recommended),
        )
        try:
            level = max(1, min(10, int(level)))
        except ValueError:
            level = recommended
        self._config.set("brain_power", value=level)
        console.print(f"[green]✓ Brain power set to {level} ({BRAIN_POWER_PRESETS[level]['name']})[/green]")

        # Step 3: Provider Setup
        console.print("\n[bold cyan]Step 3/5: AI Provider Setup[/bold cyan]")
        console.print("[dim]Choose which AI providers to use. You need at least one.[/dim]\n")
        await self._setup_providers()

        # Step 4: Voice Setup (Optional)
        console.print("\n[bold cyan]Step 4/5: Voice / Text-to-Speech (Optional)[/bold cyan]")
        await self._setup_voice()

        # Step 5: Final Configuration
        console.print("\n[bold cyan]Step 5/5: Final Settings[/bold cyan]")
        await self._final_settings()

        # Save
        self._config.save()

        # Done!
        self._print_complete()

    def _print_welcome(self) -> None:
        """Print welcome banner."""
        console.print(Panel(
            Text.from_markup(
                "[bold cyan]Welcome to ALD-01![/bold cyan]\n\n"
                "[dim]Advanced Local Desktop Intelligence[/dim]\n"
                "Your Personal AI Agent System\n\n"
                "This wizard will help you set up ALD-01 in just a few minutes.\n"
                "You can always change these settings later with [bold]ald-01 config[/bold]"
            ),
            title="[bold]🚀 ALD-01 Setup Wizard[/bold]",
            border_style="cyan",
            padding=(1, 3),
        ))

    def _display_hardware(self, hw: Dict[str, Any]) -> None:
        """Display detected hardware."""
        table = Table(show_header=False, border_style="dim")
        table.add_column("Property", style="bold")
        table.add_column("Value")

        table.add_row("Platform", f"{hw['platform']} ({hw['architecture']})")
        table.add_row("CPU", f"{hw['cpu']['cores_logical']} cores @ {hw['cpu']['frequency_mhz']} MHz")
        table.add_row("RAM", f"{hw['memory']['total_gb']} GB total, {hw['memory']['available_gb']} GB free")
        table.add_row("Disk", f"{hw['disk']['free_gb']} GB free")
        table.add_row("GPU", hw['gpu']['name'] if hw['gpu']['available'] else "None detected")
        table.add_row("Recommendation", f"[cyan]Brain Power Level {hw['recommended_brain_power']}[/cyan]")

        console.print(table)

    def _display_brain_presets(self) -> None:
        """Display brain power presets."""
        table = Table(title="Brain Power Levels", header_style="bold cyan")
        table.add_column("Level", justify="center")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Autonomous")

        for level, preset in BRAIN_POWER_PRESETS.items():
            auto = "✓" if preset.get("autonomous") else ""
            table.add_row(
                str(level),
                preset["name"],
                preset["description"],
                auto,
            )

        console.print(table)

    async def _setup_providers(self) -> None:
        """Setup AI providers."""
        # Check Ollama first
        console.print("[bold]Local AI (Ollama):[/bold]")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    console.print(f"  [green]✓ Ollama detected with {len(models)} model(s): {', '.join(models[:3])}[/green]")
                    self._config.set("providers", "ollama", "enabled", value=True)
        except Exception:
            console.print("  [yellow]⚠ Ollama not running. Install from ollama.ai for local AI[/yellow]")

        # Free cloud providers
        console.print("\n[bold]Free Cloud Providers:[/bold]")
        table = Table(show_header=True, header_style="bold green")
        table.add_column("#")
        table.add_column("Provider")
        table.add_column("Model")
        table.add_column("Status")
        table.add_column("Env Variable")

        free_list = [(k, v) for k, v in FREE_PROVIDERS.items() if v.get("free_tier")]
        for i, (key, preset) in enumerate(free_list, 1):
            env_key = preset.get("env_key", "")
            has_key = bool(os.environ.get(env_key, ""))
            status = "[green]✓ Key Set[/green]" if has_key else "[dim]Not set[/dim]"
            table.add_row(str(i), preset["name"], preset["default_model"], status, env_key)

        console.print(table)

        console.print("\n[dim]To add a provider, set its API key as an environment variable:[/dim]")
        console.print("[dim]  Windows:  set GROQ_API_KEY=gsk_xxxx[/dim]")
        console.print("[dim]  Linux:    export GROQ_API_KEY=gsk_xxxx[/dim]")

        # Check if any key is set
        add_key = Confirm.ask("\nWould you like to enter an API key now?", default=False)
        if add_key:
            console.print("\nEnter the provider number from the table above:")
            choice = Prompt.ask("Provider #", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(free_list):
                    key, preset = free_list[idx]
                    api_key = Prompt.ask(f"Enter {preset['name']} API key", password=True)
                    if api_key:
                        env_key = preset.get("env_key", "")
                        os.environ[env_key] = api_key
                        console.print(f"[green]✓ {preset['name']} configured![/green]")
                        console.print(f"  [dim]To make permanent, add to your shell profile: export {env_key}={api_key[:8]}...[/dim]")
            except (ValueError, IndexError):
                console.print("[yellow]Invalid selection, skipped.[/yellow]")

    async def _setup_voice(self) -> None:
        """Setup voice/TTS."""
        enable_voice = Confirm.ask("Enable voice output? (ALD-01 can speak its responses)", default=False)

        if enable_voice:
            self._config.set("voice", "enabled", value=True)

            # Check available engines
            engines = []
            try:
                import edge_tts
                engines.append("edge-tts (Microsoft Neural TTS — recommended)")
            except ImportError:
                pass
            try:
                import pyttsx3
                engines.append("pyttsx3 (offline)")
            except ImportError:
                pass

            if engines:
                console.print(f"[green]✓ Available engines: {', '.join(engines)}[/green]")
            else:
                console.print("[yellow]No TTS engines installed. To enable voice:[/yellow]")
                console.print("  [cyan]pip install edge-tts[/cyan]   (recommended, free Microsoft voices)")
                console.print("  [cyan]pip install pyttsx3[/cyan]    (offline fallback)")
                self._config.set("voice", "enabled", value=False)
        else:
            self._config.set("voice", "enabled", value=False)
            console.print("[dim]Voice disabled. Enable later with: ald-01 config set voice.enabled true[/dim]")

    async def _final_settings(self) -> None:
        """Final configuration options."""
        # Dashboard port
        port = Prompt.ask("Dashboard port", default="7860")
        try:
            self._config.set("dashboard", "port", value=int(port))
        except ValueError:
            self._config.set("dashboard", "port", value=7860)

        # Auto-open browser
        auto_open = Confirm.ask("Auto-open dashboard in browser?", default=True)
        self._config.set("dashboard", "auto_open", value=auto_open)

        # Tool permissions
        console.print("\n[bold]Tool Permissions:[/bold]")
        console.print("[dim]ALD-01 can access your filesystem and run commands.[/dim]")
        console.print("[dim]These can be toggled anytime from the dashboard or config.[/dim]")

        enable_terminal = Confirm.ask("Enable terminal access? (execute shell commands)", default=False)
        self._config.set("tools", "terminal", "enabled", value=enable_terminal)

        enable_code = Confirm.ask("Enable code execution? (run Python in sandbox)", default=False)
        self._config.set("tools", "code_execute", "enabled", value=enable_code)

    def _print_complete(self) -> None:
        """Print completion message."""
        console.print()
        console.print(Panel(
            Text.from_markup(
                "[bold green]✓ Setup Complete![/bold green]\n\n"
                "Your ALD-01 is ready to go. Here's what you can do:\n\n"
                "  [cyan]ald-01 chat[/cyan]       — Start an interactive chat\n"
                "  [cyan]ald-01 ask 'question'[/cyan] — Quick question\n"
                "  [cyan]ald-01 dashboard[/cyan]   — Launch web UI\n"
                "  [cyan]ald-01 doctor[/cyan]      — Run system diagnostics\n"
                "  [cyan]ald-01 status[/cyan]      — Check system status\n"
                "  [cyan]ald-01 provider list[/cyan] — See AI providers\n"
                "  [cyan]ald-01 voice test[/cyan]  — Test voice output\n\n"
                "[dim]Config saved to ~/.ald01/config.yaml[/dim]\n"
                "[dim]Change settings: ald-01 config set <key> <value>[/dim]"
            ),
            title="[bold]🎉 Ready![/bold]",
            border_style="green",
            padding=(1, 3),
        ))


async def run_onboarding() -> None:
    """Run the onboarding wizard."""
    wizard = OnboardingWizard()
    await wizard.run()
