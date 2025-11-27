import json
import logging
from typing import Any, Dict, Tuple

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()


def chat_json(system_prompt: str, user_prompt: str, *, model: str, temperature: float | None = None) -> Tuple[Dict[str, Any], str]:
    used_temp = settings.OPENAI_TEMPERATURE if temperature is None else float(temperature)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=used_temp,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except Exception:
        logger.exception("LLM returned non-JSON content: %s", raw[:3000])
        raise

    return data, model
