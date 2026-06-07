"""Telegram bot interface for the orchestrator."""
from __future__ import annotations
import logging
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters,
)

if TYPE_CHECKING:
    from .engine import Orchestrator

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that wraps the orchestrator."""

    def __init__(self, token: str, orchestrator: Orchestrator, allowed_users: list[int] | None = None):
        self.token = token
        self.orchestrator = orchestrator
        self.allowed_users = set(allowed_users) if allowed_users else None
        self.app: Application | None = None

    def _is_allowed(self, user_id: int) -> bool:
        if self.allowed_users is None:
            return True
        return user_id in self.allowed_users

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        await update.message.reply_text(
            "Agent Orchestrator ready.\n\n"
            "Commands:\n"
            "/run <task.yaml> — Execute task file\n"
            "/tasks — List available tasks\n"
            "/plugins — List loaded plugins\n"
            "/history — Recent task history\n"
            "/status — System status"
        )

    async def cmd_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /run <task.yaml>")
            return

        task_path = Path(args[0])
        if not task_path.exists():
            # Try relative to tasks directory
            task_path = Path("tasks") / args[0]
        if not task_path.exists():
            await update.message.reply_text(f"Task file not found: {args[0]}")
            return

        await update.message.reply_text(f"Running: {task_path.name}...")
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.orchestrator.run_task_file, task_path
            )
            await update.message.reply_text(f"```\n{result.summary()}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def cmd_plugins(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        plugins = self.orchestrator.plugins.list_plugins()
        if not plugins:
            await update.message.reply_text("No plugins loaded.")
            return
        lines = ["Loaded Plugins:"]
        for p in plugins:
            methods = ", ".join(p["methods"])
            lines.append(f"  {p['name']}: {methods}")
        await update.message.reply_text("\n".join(lines))

    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        history = self.orchestrator.get_history(5)
        if not history:
            await update.message.reply_text("No task history.")
            return
        lines = ["Recent Tasks:"]
        for r in history:
            icon = "OK" if r.success else "FAIL"
            lines.append(f"  [{icon}] {r.task_name} ({r.duration_ms}ms)")
        await update.message.reply_text("\n".join(lines))

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        plugins = self.orchestrator.plugins.list_plugins()
        history = self.orchestrator.get_history(100)
        success = sum(1 for r in history if r.success)
        await update.message.reply_text(
            f"Status:\n"
            f"  Plugins: {len(plugins)}\n"
            f"  Tasks run: {len(history)}\n"
            f"  Success rate: {success}/{len(history)}" if history else "  No tasks run yet"
        )

    async def cmd_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        tasks_dir = Path("tasks")
        if not tasks_dir.exists():
            await update.message.reply_text("No tasks directory found.")
            return
        files = sorted(tasks_dir.glob("*.yaml")) + sorted(tasks_dir.glob("*.yml"))
        if not files:
            await update.message.reply_text("No task files found.")
            return
        lines = ["Available Tasks:"]
        for f in files:
            lines.append(f"  {f.name}")
        await update.message.reply_text("\n".join(lines))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle natural language messages — future: LLM integration."""
        if not self._is_allowed(update.effective_user.id):
            return
        text = update.message.text
        await update.message.reply_text(
            f"Received: {text[:100]}\n"
            "Use /run <task.yaml> to execute tasks."
        )

    def run(self) -> None:
        """Start the bot (blocking)."""
        self.app = Application.builder().token(self.token).build()
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("run", self.cmd_run))
        self.app.add_handler(CommandHandler("plugins", self.cmd_plugins))
        self.app.add_handler(CommandHandler("history", self.cmd_history))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("tasks", self.cmd_tasks))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        logger.info("Telegram bot starting...")
        self.app.run_polling(drop_pending_updates=True)
