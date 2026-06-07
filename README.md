# Agent Task Orchestrator

Run multi-step tasks from natural language with a plugin system, Telegram bot interface, and cron scheduling.

## Features

- **Multi-step task execution** — define tasks in YAML, execute sequentially with context passing
- **Plugin system** — extend with custom plugins, auto-discover from directory
- **Telegram bot** — control orchestrator from Telegram with commands
- **Cron scheduler** — schedule recurring tasks with standard cron expressions
- **Retry & error handling** — configurable retries per step, detailed error reporting
- **Context passing** — step outputs available to subsequent steps via `$ref` syntax

## Quick Start

```bash
# Install
pip install -e .

# Create config
cp config.yaml.example config.yaml

# Run a task
agent-orch run tasks/check_url.yaml

# List plugins
agent-orch plugins

# Start Telegram bot
agent-orch bot

# Start cron scheduler
agent-orch serve
```

## Task Definition

Tasks are defined in YAML files:

```yaml
name: my-task
description: Example multi-step task
schedule: "0 9 * * *"  # Optional: cron expression

steps:
  - name: fetch-data
    handler: http.get
    params:
      url: "https://api.example.com/data"
    retries: 2

  - name: check-response
    handler: text.contains
    params:
      text: "$step_fetch-data"  # Reference previous step output
      keyword: "success"

  - name: save-result
    handler: file.write
    params:
      path: "output/result.json"
      content: "$step_fetch-data"
```

## Plugins

Plugins are Python classes that extend `Plugin`:

```python
from agent_orchestrator.plugin import Plugin

class MyPlugin(Plugin):
    name = "myplugin"
    description = "My custom plugin"

    def setup(self, config: dict) -> None:
        self.api_key = config.get("api_key", "")

    def my_method(self, param: str) -> str:
        return f"Result: {param}"
```

Place plugin files in `plugins/` directory. They're auto-discovered on startup.

### Built-in Plugins

| Plugin | Methods | Description |
|--------|---------|-------------|
| `http` | `get`, `post`, `check_url` | HTTP requests |
| `text` | `contains`, `extract_json`, `truncate`, `lines` | Text processing |
| `file` | `read`, `write`, `exists`, `list_dir` | File operations |

## Telegram Bot

Set `telegram.bot_token` in config.yaml (get from [@BotFather](https://t.me/BotFather)):

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  allowed_users: [123456789]  # Optional: restrict access
```

Commands:
- `/run <task.yaml>` — Execute a task file
- `/tasks` — List available tasks
- `/plugins` — List loaded plugins
- `/history` — Recent task history
- `/status` — System status

## Cron Scheduling

Add `schedule` field to any task YAML:

```yaml
name: daily-check
schedule: "0 9 * * *"  # Every day at 9 AM
steps:
  - name: check
    handler: http.check_url
    params:
      url: "https://example.com"
```

Start the scheduler:
```bash
agent-orch serve
```

## Context & Variables

Step outputs are available to subsequent steps via `$step_<name>`:

```yaml
steps:
  - name: fetch
    handler: http.get
    params:
      url: "https://api.example.com"
  - name: parse
    handler: text.extract_json
    params:
      text: "$step_fetch"  # Uses output from 'fetch' step
```

## Project Structure

```
agent-orchestrator/
├── src/agent_orchestrator/
│   ├── __init__.py
│   ├── cli.py            # CLI entry point
│   ├── engine.py          # Core orchestrator
│   ├── plugin.py          # Plugin system
│   ├── scheduler.py       # Cron scheduler
│   ├── task.py            # Task/result types
│   └── telegram_bot.py    # Telegram interface
├── plugins/               # Plugin directory (auto-discovered)
│   ├── http_plugin.py
│   ├── text_plugin.py
│   └── file_plugin.py
├── tasks/                 # Task definitions
│   ├── check_url.yaml
│   └── hello_cron.yaml
├── tests/
├── config.yaml.example
├── pyproject.toml
└── README.md
```

## License

MIT
