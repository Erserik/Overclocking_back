from typing import Any, Dict, Tuple
import logging

from django.conf import settings

from ...llm_client import chat_json
from . import prompt, schema

logger = logging.getLogger(__name__)


def generate(case_context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Генерация BPMN-диаграммы через LLM.

    Возвращает:
    - structured_data (dict) c полями plantuml, notes
    - used_model (str)
    """

    system_prompt = prompt.SYSTEM_PROMPT
    user_prompt = prompt.build_user_prompt(case_context)

    logger.info(
        "BPMN | send to LLM, case_id=%s, title=%s",
        case_context["case"]["id"],
        case_context["case"]["title"],
    )

    raw_data, used_model = chat_json(
        system_prompt,
        user_prompt,
        model=getattr(settings, "OPENAI_MODEL_BPMN", settings.OPENAI_MODEL_SCOPE),
    )

    # DEBUG: что вернул GPT
    print("\n========== RAW BPMN FROM LLM ==========")
    print(raw_data)
    print("=======================================\n")

    logger.info(
        "BPMN | raw_data type=%s keys=%s",
        type(raw_data),
        list(raw_data.keys()) if isinstance(raw_data, dict) else None,
    )

    # Приводим к стабильной схеме
    data = schema.validate(raw_data)

    # DEBUG: что после валидации
    print("\n========== VALIDATED BPMN DATA ==========")
    print(data)
    print("plantuml (first 400 chars):")
    print((data or {}).get("plantuml", "")[:400])
    print("=========================================\n")

    logger.info(
        "BPMN | after validate, has_plantuml=%s",
        bool((data or {}).get("plantuml")),
    )

    return data, used_model
