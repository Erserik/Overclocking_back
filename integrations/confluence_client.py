# integrations/confluence_client.py
from typing import Any, Dict, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ConfluenceClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.CONFLUENCE_BASE_URL).rstrip("/")
        self.username = username or settings.CONFLUENCE_USERNAME
        self.api_token = api_token or settings.CONFLUENCE_API_TOKEN
        self.api_base = f"{self.base_url}/rest/api"
        self.auth = HTTPBasicAuth(self.username, self.api_token)

    def _request(self, method: str, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        resp = requests.request(method, url, auth=self.auth, json=json)
        resp.raise_for_status()
        return resp.json()

    def create_page(self, space_key: str, title: str, html_body: str) -> Tuple[str, str]:
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": html_body,
                    "representation": "storage",
                }
            },
        }
        data = self._request("POST", "content", payload)
        page_id = data["id"]
        webui = data.get("_links", {}).get("webui", "")
        url = f"{self.base_url}{webui}"
        logger.info("Created Confluence page %s for space %s", page_id, space_key)
        return page_id, url
