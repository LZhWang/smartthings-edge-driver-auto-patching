from dataclasses import dataclass
from typing import List, Dict, Any

import requests


class HomeAssistantError(RuntimeError):
    """Raised when Home Assistant API calls fail."""


@dataclass
class HomeAssistantClient:
    base_url: str
    token: str
    timeout: float = 10.0

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get_states(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url.rstrip('/')}/api/states"
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        if resp.status_code != 200:
            raise HomeAssistantError(f"GET {url} failed: {resp.status_code} {resp.text}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise HomeAssistantError(f"Invalid JSON from {url}") from exc
        if not isinstance(data, list):
            raise HomeAssistantError(f"Unexpected states payload type: {type(data)}")
        return data
