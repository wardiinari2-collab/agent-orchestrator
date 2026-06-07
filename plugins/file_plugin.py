"""Example plugin: File operations."""
from agent_orchestrator.plugin import Plugin
from pathlib import Path


class FilePlugin(Plugin):
    name = "file"
    description = "File read/write operations"

    def read(self, path: str) -> str:
        """Read file contents."""
        return Path(path).read_text()

    def write(self, path: str, content: str) -> bool:
        """Write content to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content)
        return True

    def exists(self, path: str) -> bool:
        """Check if file exists."""
        return Path(path).exists()

    def list_dir(self, path: str, pattern: str = "*") -> list:
        """List files in directory."""
        return [str(f.name) for f in Path(path).glob(pattern) if f.is_file()]
