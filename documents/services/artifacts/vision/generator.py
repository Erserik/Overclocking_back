from typing import Any, Dict, Tuple
from django.conf import settings

from . import prompt, schema
from ...llm_client import chat_json


def generate(case_context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    user_prompt = prompt.build_user_prompt(case_context)
    data, used_model = chat_json(prompt.SYSTEM_PROMPT, user_prompt, model=settings.OPENAI_MODEL_VISION)
    data = schema.validate(data)
    return data, used_model
