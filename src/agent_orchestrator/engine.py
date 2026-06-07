"""Core orchestrator engine — executes multi-step tasks."""
from __future__ import annotations
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml

from .task import Task, TaskStep, TaskResult, StepResult, TaskStatus
from .plugin import PluginManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main engine — loads config, plugins, and executes tasks."""

    def __init__(self, config_path: str | Path | None = None):
        self.config: dict = {}
        self.plugins = PluginManager()
        self._hooks: dict[str, list[Callable]] = {}
        self._task_history: list[TaskResult] = []

        if config_path:
            self.load_config(config_path)

    def load_config(self, path: str | Path) -> None:
        """Load YAML configuration."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path) as f:
            self.config = yaml.safe_load(f) or {}
        # Load plugins from configured directory
        plugin_dir = self.config.get("plugins", {}).get("directory", "plugins")
        plugin_config = self.config.get("plugins", {}).get("config", {})
        base = path.parent
        loaded = self.plugins.load_directory(base / plugin_dir, plugin_config)
        logger.info(f"Loaded {loaded} plugins from {base / plugin_dir}")

    def hook(self, event: str) -> Callable:
        """Decorator to register a hook (on_start, on_complete, on_error)."""
        def decorator(fn):
            self._hooks.setdefault(event, []).append(fn)
            return fn
        return decorator

    def _fire(self, event: str, **kwargs) -> None:
        for fn in self._hooks.get(event, []):
            try:
                fn(**kwargs)
            except Exception as e:
                logger.error(f"Hook {event} error: {e}")

    def execute(self, task: Task) -> TaskResult:
        """Execute a task's steps sequentially."""
        result = TaskResult(
            task_id=task.id,
            task_name=task.name,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self._fire("on_start", task=task, result=result)
        logger.info(f"Executing task: {task.name} ({len(task.steps)} steps)")

        context: dict[str, Any] = {"task": task, "config": self.config}

        for step in task.steps:
            step_result = self._execute_step(step, context)
            result.steps.append(step_result)
            context[f"step_{step.name}"] = step_result.output

            if step_result.status == TaskStatus.FAILED:
                result.status = TaskStatus.FAILED
                result.error = step_result.error
                break
        else:
            result.status = TaskStatus.SUCCESS

        result.finished_at = datetime.utcnow()
        self._task_history.append(result)
        self._fire("on_complete" if result.success else "on_error", task=task, result=result)
        logger.info(f"Task {task.name}: {result.status.value} ({result.duration_ms}ms)")
        return result

    def _execute_step(self, step: TaskStep, context: dict) -> StepResult:
        """Execute a single step with retries."""
        start = time.monotonic()

        for attempt in range(step.retries + 1):
            try:
                # Resolve params from context
                resolved_params = self._resolve_params(step.params, context)

                # Call plugin method
                method = self.plugins.get_method(step.handler)
                if not method:
                    return StepResult(
                        step_name=step.name,
                        status=TaskStatus.FAILED,
                        error=f"Handler '{step.handler}' not found",
                    )

                output = method(**resolved_params)
                duration = int((time.monotonic() - start) * 1000)
                return StepResult(
                    step_name=step.name,
                    status=TaskStatus.SUCCESS,
                    output=output,
                    duration_ms=duration,
                )

            except Exception as e:
                if attempt < step.retries:
                    logger.warning(f"Step '{step.name}' attempt {attempt + 1} failed: {e}, retrying...")
                    continue
                duration = int((time.monotonic() - start) * 1000)
                return StepResult(
                    step_name=step.name,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    duration_ms=duration,
                )

    def _resolve_params(self, params: dict, context: dict) -> dict:
        """Resolve $ref variables in params from context."""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                ref = value[1:]
                resolved[key] = context.get(ref, value)
            else:
                resolved[key] = value
        return resolved

    def run_task_file(self, path: str | Path) -> TaskResult:
        """Load and execute a task from YAML file."""
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        task = Task.from_dict(data)
        return self.execute(task)

    def get_history(self, limit: int = 10) -> list[TaskResult]:
        """Get recent task execution history."""
        return self._task_history[-limit:]

    def shutdown(self) -> None:
        """Cleanup all plugins."""
        self.plugins.shutdown()
