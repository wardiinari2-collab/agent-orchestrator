"""Example plugin: HTTP requests."""
from agent_orchestrator.plugin import Plugin
import httpx


class HttpPlugin(Plugin):
    name = "http"
    description = "Make HTTP requests"

    def setup(self, config: dict) -> None:
        self.timeout = config.get("timeout", 30)

    def get(self, url: str, headers: dict | None = None) -> dict:
        """GET request. Returns {status, body, headers}."""
        resp = httpx.get(url, headers=headers, timeout=self.timeout, follow_redirects=True)
        return {
            "status": resp.status_code,
            "body": resp.text[:10000],
            "headers": dict(resp.headers),
        }

    def post(self, url: str, data: str = "", headers: dict | None = None) -> dict:
        """POST request."""
        resp = httpx.post(url, content=data, headers=headers, timeout=self.timeout, follow_redirects=True)
        return {
            "status": resp.status_code,
            "body": resp.text[:10000],
        }

    def check_url(self, url: str, expected_status: int = 200) -> bool:
        """Check if URL returns expected status."""
        resp = httpx.head(url, timeout=self.timeout, follow_redirects=True)
        return resp.status_code == expected_status
