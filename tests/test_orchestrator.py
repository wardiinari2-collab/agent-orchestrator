"""Basic orchestrator tests."""
import pytest
from agent_orchestrator.task import Task, TaskStep, TaskStatus
from agent_orchestrator.plugin import Plugin, PluginManager


class MockPlugin(Plugin):
    name = "mock"
    description = "Test plugin"

    def hello(self, name: str = "world") -> str:
        return f"hello {name}"

    def fail(self) -> None:
        raise ValueError("intentional failure")


def test_plugin_register():
    pm = PluginManager()
    pm.register(MockPlugin())
    assert "mock.hello" in [k for k in pm._methods]


def test_plugin_call():
    pm = PluginManager()
    pm.register(MockPlugin())
    result = pm.call("mock.hello", name="test")
    assert result == "hello test"


def test_plugin_call_not_found():
    pm = PluginManager()
    with pytest.raises(KeyError):
        pm.call("nonexistent.method")


def test_task_from_dict():
    data = {
        "name": "test",
        "steps": [
            {"name": "step1", "handler": "mock.hello"},
            {"name": "step2", "handler": "mock.hello", "params": {"name": "custom"}},
        ],
    }
    task = Task.from_dict(data)
    assert task.name == "test"
    assert len(task.steps) == 2
    assert task.steps[0].handler == "mock.hello"


def test_task_result_summary():
    from agent_orchestrator.task import TaskResult, StepResult
    result = TaskResult(
        task_id="test",
        task_name="test_task",
        status=TaskStatus.SUCCESS,
        steps=[
            StepResult(step_name="step1", status=TaskStatus.SUCCESS, duration_ms=100),
        ],
    )
    summary = result.summary()
    assert "test_task" in summary
    assert "OK" in summary
