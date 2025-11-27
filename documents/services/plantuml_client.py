import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_PLANTUML_SERVER_URL = "https://www.plantuml.com/plantuml/png"


def render_plantuml_png(plantuml_text: str, timeout: int = 15) -> Optional[bytes]:
    """
    Отправляет PlantUML-текст на сервер и возвращает бинарник PNG.

    В прототипе используем публичный сервер.
    В бою URL должен указывать на внутренний PlantUML-сервер банка.
    """

    server_url = getattr(settings, "PLANTUML_SERVER_URL", DEFAULT_PLANTUML_SERVER_URL)

    try:
        # Сервер PlantUML поддерживает POST c raw body
        resp = requests.post(
            server_url,
            data=plantuml_text.encode("utf-8"),
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.content
    except Exception:
        logger.exception("Failed to render PlantUML PNG via %s", server_url)
        return None
