# documents/services/artifacts/context_diagram/generator.py

from typing import Any, Dict, Tuple
import logging

from django.conf import settings

from ...llm_client import chat_json
from . import prompt, schema

logger = logging.getLogger(__name__)


def generate(case_context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Генерация контекстной диаграммы через LLM.

    Возвращает:
    - structured_data (dict) c полем plantuml
    - used_model (str)
    """

    system_prompt = prompt.SYSTEM_PROMPT
    user_prompt = prompt.build_user_prompt(case_context)

    logger.info(
        "CONTEXT_DIAGRAM | send to LLM, case_id=%s, title=%s",
        case_context["case"]["id"],
        case_context["case"]["title"],
    )

    raw_data, used_model = chat_json(
        system_prompt,
        user_prompt,
        model=getattr(settings, "OPENAI_MODEL_CONTEXT", settings.OPENAI_MODEL_SCOPE),
    )

    # ==== DEBUG: смотрим, что реально вернул GPT ====
    print("\n========== RAW CONTEXT DIAGRAM FROM LLM ==========")
    print(raw_data)
    print("=======================================\n")

    # Валидация / нормализация
    data = schema.validate(raw_data)

    print("\n========== VALIDATED CONTEXT DIAGRAM DATA ==========")
    print(data)
    print("plantuml (first 400 chars):")
    print((data or {}).get("plantuml", "")[:400])
    print("=========================================\n")

    logger.info(
        "CONTEXT_DIAGRAM | after validate, has_plantuml=%s",
        bool((data or {}).get("plantuml")),
    )

    return data, used_model
