# integrations/confluence/handler.py

import requests
import time
from typing import List, Dict, Optional, Any
from requests.auth import HTTPBasicAuth


class ConfluenceHandler:
    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        default_space_key: Optional[str] = None,
        connection_timeout: int = 30000,
        request_timeout: int = 30000,
    ):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.default_space_key = default_space_key
        self.connection_timeout = connection_timeout / 1000
        self.request_timeout = request_timeout / 1000
        self.auth = HTTPBasicAuth(username, api_token)
        self.api_base = f"{self.base_url}/rest/api"

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
    ) -> Dict[str, Any]:
        url = f"{self.api_base}/{endpoint}"

        response = requests.request(
            method=method,
            url=url,
            auth=self.auth,
            params=params,
            timeout=(self.connection_timeout, self.request_timeout),
        )
        response.raise_for_status()
        return response.json()

    def get_all_spaces(self) -> List[Dict[str, Any]]:
        spaces: List[Dict[str, Any]] = []
        start = 0
        limit = 100

        while True:
            response = self._make_request(
                "space",
                params={"start": start, "limit": limit},
            )
            results = response.get("results", [])
            spaces.extend(results)

            if len(results) < limit:
                break

            start += limit
            time.sleep(0.1)

        return spaces
