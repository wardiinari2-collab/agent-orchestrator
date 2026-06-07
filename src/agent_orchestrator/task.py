"""Task definition and result types."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class TaskStep:
    """Single step within a task."""
    name: str
    handler: str  # plugin.method
    params: dict[str, Any] = field(default_factory=dict)
    timeout: int = 60
    retries: int = 0
    condition: str | None = None  # skip if condition not met


@dataclass
class Task:
    """Multi-step task definition."""
    name: str
    steps: list[TaskStep] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    schedule: str | None = None  # cron expression
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        steps = [TaskStep(**s) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            steps=steps,
            description=data.get("description", ""),
            schedule=data.get("schedule"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class StepResult:
    """Result of a single step execution."""
    step_name: str
    status: TaskStatus
    output: Any = None
    error: str | None = None
    duration_ms: int = 0


@dataclass
class TaskResult:
    """Aggregated result of task execution."""
    task_id: str
    task_name: str
    status: TaskStatus
    steps: list[StepResult] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None

    @property
    def duration_ms(self) -> int:
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds() * 1000)
        return 0

    @property
    def success(self) -> bool:
        return self.status == TaskStatus.SUCCESS

    def summary(self) -> str:
        lines = [f"Task: {self.task_name} [{self.status.value}]"]
        for s in self.steps:
            icon = "OK" if s.status == TaskStatus.SUCCESS else "FAIL"
            lines.append(f"  [{icon}] {s.step_name} ({s.duration_ms}ms)")
            if s.error:
                lines.append(f"       Error: {s.error}")
        if self.duration_ms:
            lines.append(f"Total: {self.duration_ms}ms")
        return "\n".join(lines)
