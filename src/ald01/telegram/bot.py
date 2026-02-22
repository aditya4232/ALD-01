"""
ALD-01 Telegram Bot
Optional remote control and notifications via Telegram.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from ald01.config import get_config
from ald01.core.orchestrator import get_orchestrator

logger = logging.getLogger("ald01.telegram")


class TelegramBot:
    """
    Telegram bot for remote ALD-01 control.
    Uses the Telegram Bot API directly (no external SDK needed).
    
    Commands:
    /ask <question> — Ask ALD-01 a question
    /status — Get system status
    /brain <level> — Set brain power
    /agents — List agents
    /providers — List providers
    /help — Show available commands
    """

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(self, token: Optional[str] = None, allowed_users: Optional[list] = None):
        config = get_config()
        self.token = token or config.get("telegram", "token", default="") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.allowed_users = allowed_users or config.get("telegram", "allowed_users", default=[])
        self._running = False
        self._offset = 0

    @property
    def api_url(self) -> str:
        return self.BASE_URL.format(token=self.token)

    def is_configured(self) -> bool:
        return bool(self.token)

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to a Telegram chat."""
        if not self.is_configured():
            return False

        # Telegram message limit is 4096 chars
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (truncated)"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{self.api_url}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                })
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def _get_updates(self) -> list:
        """Get new messages from Telegram."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{self.api_url}/getUpdates", params={
                    "offset": self._offset,
                    "timeout": 25,
                })
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("result", [])
        except Exception as e:
            logger.debug(f"Telegram update error: {e}")
        return []

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle an incoming Telegram message."""
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return

        # Authorization check
        if self.allowed_users and user_id not in self.allowed_users:
            await self.send_message(chat_id, "⛔ Unauthorized. Your user ID is not in the allowed list.")
            return

        # Command routing
        if text.startswith("/ask "):
            query = text[5:].strip()
            await self._cmd_ask(chat_id, query)
        elif text == "/status":
            await self._cmd_status(chat_id)
        elif text.startswith("/brain "):
            level = text[7:].strip()
            await self._cmd_brain(chat_id, level)
        elif text == "/agents":
            await self._cmd_agents(chat_id)
        elif text == "/providers":
            await self._cmd_providers(chat_id)
        elif text in ["/start", "/help"]:
            await self._cmd_help(chat_id)
        else:
            # Treat as a general question
            await self._cmd_ask(chat_id, text)

    async def _cmd_ask(self, chat_id: int, query: str) -> None:
        """Process a question."""
        await self.send_message(chat_id, "🧠 Thinking...")
        try:
            orch = get_orchestrator()
            response = await orch.process_query(query)
            reply = (
                f"<b>ALD-01 ({response.agent_name})</b>\n\n"
                f"{response.content}\n\n"
                f"<i>Model: {response.model} | {response.latency_ms:.0f}ms</i>"
            )
            await self.send_message(chat_id, reply)
        except Exception as e:
            await self.send_message(chat_id, f"❌ Error: {e}")

    async def _cmd_status(self, chat_id: int) -> None:
        """Send system status."""
        orch = get_orchestrator()
        s = orch.get_status()
        status = (
            f"<b>🤖 ALD-01 Status</b>\n\n"
            f"Status: {s['status']}\n"
            f"Uptime: {s['uptime_human']}\n"
            f"Brain Power: {s['brain_power']} ({s['brain_power_name']})\n"
            f"Requests: {s['total_requests']}\n"
            f"Providers: {s['providers']['online_providers']}/{s['providers']['total_providers']}\n"
            f"Messages: {s['memory']['messages']}\n"
            f"DB Size: {s['memory']['db_size_mb']} MB"
        )
        await self.send_message(chat_id, status)

    async def _cmd_brain(self, chat_id: int, level_str: str) -> None:
        """Set brain power."""
        try:
            level = max(1, min(10, int(level_str)))
            config = get_config()
            config.brain_power = level
            config.save()
            from ald01.config import BRAIN_POWER_PRESETS
            name = BRAIN_POWER_PRESETS[level]["name"]
            await self.send_message(chat_id, f"✅ Brain power set to {level} ({name})")
        except ValueError:
            await self.send_message(chat_id, "⚠️ Invalid level. Use 1-10.")

    async def _cmd_agents(self, chat_id: int) -> None:
        """List agents."""
        orch = get_orchestrator()
        agents = orch.get_agents()
        lines = ["<b>🤖 Agents</b>\n"]
        for name, a in agents.items():
            status = "✅" if a["enabled"] else "❌"
            lines.append(f"{status} <b>{a['display_name']}</b> — {a['expertise']}")
        await self.send_message(chat_id, "\n".join(lines))

    async def _cmd_providers(self, chat_id: int) -> None:
        """List providers."""
        from ald01.providers.manager import get_provider_manager
        mgr = get_provider_manager()
        stats = mgr.get_stats()
        lines = ["<b>🔌 Providers</b>\n"]
        for name, p in stats.get("providers", {}).items():
            status = "🟢" if p.get("online") else "🔴"
            lines.append(f"{status} {name} ({p.get('latency_ms', 0):.0f}ms)")
        await self.send_message(chat_id, "\n".join(lines))

    async def _cmd_help(self, chat_id: int) -> None:
        """Show help."""
        help_text = (
            "<b>🤖 ALD-01 Telegram Bot</b>\n\n"
            "Commands:\n"
            "/ask &lt;question&gt; — Ask a question\n"
            "/status — System status\n"
            "/brain &lt;1-10&gt; — Set brain power\n"
            "/agents — List AI agents\n"
            "/providers — List AI providers\n"
            "/help — Show this help\n\n"
            "Or just type any message to chat directly!"
        )
        await self.send_message(chat_id, help_text)

    async def start_polling(self) -> None:
        """Start long-polling for messages."""
        if not self.is_configured():
            logger.warning("Telegram bot token not set. Skipping.")
            return

        self._running = True
        logger.info("Telegram bot started polling...")

        while self._running:
            try:
                updates = await self._get_updates()
                for update in updates:
                    self._offset = update.get("update_id", 0) + 1
                    message = update.get("message")
                    if message:
                        await self._handle_message(message)
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop polling."""
        self._running = False
        logger.info("Telegram bot stopped.")


# Singleton
_telegram_bot: Optional[TelegramBot] = None


def get_telegram_bot() -> TelegramBot:
    """Get or create the global Telegram bot."""
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = TelegramBot()
    return _telegram_bot
