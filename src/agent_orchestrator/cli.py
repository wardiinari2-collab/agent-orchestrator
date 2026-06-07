"""CLI entry point."""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

from .engine import Orchestrator
from .scheduler import Scheduler


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent Task Orchestrator — run multi-step tasks from YAML",
        prog="agent-orch",
    )
    parser.add_argument("command", choices=["run", "bot", "serve", "plugins", "tasks"],
                        help="Command to execute")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        print(f"Create one from config.yaml.example")
        sys.exit(1)

    orch = Orchestrator(config_path)

    if args.command == "run":
        if not args.args:
            print("Usage: agent-orch run <task.yaml>")
            sys.exit(1)
        for task_file in args.args:
            result = orch.run_task_file(task_file)
            print(result.summary())

    elif args.command == "plugins":
        plugins = orch.plugins.list_plugins()
        if not plugins:
            print("No plugins loaded.")
        for p in plugins:
            methods = ", ".join(p["methods"])
            print(f"  {p['name']}: {p['description']} [{methods}]")

    elif args.command == "tasks":
        tasks_dir = Path("tasks")
        if not tasks_dir.exists():
            print("No tasks/ directory found.")
            return
        for f in sorted(tasks_dir.glob("*.yaml")):
            print(f"  {f.name}")

    elif args.command == "bot":
        from .telegram_bot import TelegramBot
        token = orch.config.get("telegram", {}).get("bot_token", "")
        if not token:
            print("telegram.bot_token not set in config")
            sys.exit(1)
        allowed = orch.config.get("telegram", {}).get("allowed_users")
        bot = TelegramBot(token, orch, allowed_users=allowed)
        bot.run()

    elif args.command == "serve":
        sched = Scheduler(orch)
        tasks_dir = Path("tasks")
        if tasks_dir.exists():
            count = sched.add_tasks_directory(tasks_dir)
            print(f"Scheduled {count} tasks")
        sched.start()
        print("Scheduler running. Press Ctrl+C to stop.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sched.shutdown()
            orch.shutdown()

    orch.shutdown()
