from typing import Any, Dict, Tuple

from documents.services.llm_client import chat_json  # тот же путь, что и в bpmn
from . import prompt


MODEL_NAME = "gpt-5.1"


def generate(case_context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Генерирует structured_data для UML use case диаграммы.

    Возвращает:
    - structured_data: Dict[str, Any]
    - used_model: str
    """
    system_prompt = prompt.SYSTEM_PROMPT
    user_prompt = prompt.build_user_prompt(case_context)

    data, _raw = chat_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=MODEL_NAME,
    )

    plantuml = (data.get("plantuml") or "").strip()
    if not plantuml:
        # простой фоллбек, чтобы не падать, если модель ничего не вернула
        title = case_context.get("case", {}).get("title") or "Без названия"
        plantuml = f"""@startuml
title Use Case: {title}

actor "Пользователь" as User
actor "Бизнес-аналитик" as BA

rectangle "{title}" {{
  "Основной сценарий" as UC_Main
  "Просмотр отчётов" as UC_Reports
}}

User --> UC_Main
BA --> UC_Reports

@enduml
"""

    notes = data.get("notes") or []

    structured: Dict[str, Any] = {
        "plantuml": plantuml,
        "notes": notes,
        "raw": data,  # на всякий случай для дебага
    }

    return structured, MODEL_NAME