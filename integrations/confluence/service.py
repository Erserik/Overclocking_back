# integrations/confluence/service.py

from typing import List, Dict
from django.conf import settings

from .handler import ConfluenceHandler


def get_confluence_client() -> ConfluenceHandler:
    if not settings.CONFLUENCE_BASE_URL:
        raise RuntimeError("CONFLUENCE_BASE_URL is not configured")

    return ConfluenceHandler(
        base_url=settings.CONFLUENCE_BASE_URL,
        username=settings.CONFLUENCE_USERNAME,
        api_token=settings.CONFLUENCE_API_TOKEN,
    )


def list_spaces_short() -> List[Dict[str, str]]:
    """
    Вернуть только key + name для фронта.
    """
    client = get_confluence_client()
    spaces = client.get_all_spaces()

    result: List[Dict[str, str]] = []
    for s in spaces:
        result.append(
            {
                "key": s.get("key", ""),
                "name": s.get("name", ""),
            }
        )
    return result
