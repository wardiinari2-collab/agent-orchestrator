"""Example plugin: Text processing."""
from agent_orchestrator.plugin import Plugin
import json


class TextPlugin(Plugin):
    name = "text"
    description = "Text processing and transformation"

    def contains(self, text: str, keyword: str) -> bool:
        """Check if text contains keyword."""
        if not isinstance(text, str):
            text = str(text)
        return keyword.lower() in text.lower()

    def extract_json(self, text: str) -> dict:
        """Extract JSON from text."""
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {}

    def truncate(self, text: str, max_length: int = 200) -> str:
        """Truncate text to max length."""
        return text[:max_length] + "..." if len(text) > max_length else text

    def lines(self, text: str) -> list:
        """Split text into lines."""
        return [l.strip() for l in text.strip().split("\n") if l.strip()]
