from __future__ import annotations

import json
from typing import Any

from django.utils import timezone

from documents.models import GeneratedDocument, DocumentType
from .agent_client import chat_json
from .context_builder import build_case_context

MODEL_NAME = "gpt-5.1"

SYSTEM_PROMPT_DIAGRAM_EDIT = (
    "Ты помощник бизнес-аналитика и эксперт по PlantUML.\n\n"
    "Твоя задача — аккуратно править существующие диаграммы (BPMN, context, UML use case):\n"
    "- понимать контекст кейса и его цель;\n"
    "- учитывать текущий PlantUML-код;\n"
    "- вносить правки строго по инструкциям пользователя;\n"
    "- сохранять структуру и смысл диаграммы;\n"
    "- возвращать новый корректный PlantUML-код.\n\n"
    "Формат ответа: строго JSON-объект с полем \"plantuml\" (строка) — полный PlantUML-код от @startuml до @enduml.\n"
    "Никаких комментариев или пояснений вне JSON.\n"
)

RESPONSE_FORMAT_DIAGRAM_EDIT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "diagram_edit_response",
        "schema": {
            "type": "object",
            "properties": {
                "plantuml": {
                    "type": "string",
                    "description": "Полный PlantUML-код диаграммы от @startuml до @enduml",
                },
                "notes": {
                    "type": "string",
                    "description": "Краткое описание внесённых изменений (опционально)",
                },
            },
            "required": ["plantuml"],
            "additionalProperties": False,
        },
    },
}


def _extract_current_plantuml(doc: GeneratedDocument) -> str:
    """
    Берём текущий PlantUML:
    - сначала structured_data["plantuml"],
    - если нет — пробуем вытащить из ```plantuml``` блока в content,
    - иначе — весь content.
    """
    structured = doc.structured_data or {}
    if isinstance(structured, dict) and structured.get("plantuml"):
        return str(structured["plantuml"])

    content = (doc.content or "").strip()
    if "```plantuml" in content:
        try:
            _, after = content.split("```plantuml", 1)
            body, _ = after.split("```", 1)
            return body.strip()
        except ValueError:
            pass

    return content


def _build_user_prompt_for_diagram(
    doc: GeneratedDocument,
    instructions: str,
    plantuml: str,
) -> str:
    case = getattr(doc, "case", None)
    case_title = getattr(case, "title", "") or ""

    case_context = build_case_context(case) if case is not None else {}
    case_context_json = json.dumps(case_context, ensure_ascii=False, indent=2)

    return (
        f"Тип диаграммы: {doc.doc_type}\n"
        f"Кейс: {case_title}\n\n"
        f"JSON-контекст кейса (ответы клиента, уточняющие вопросы и т.п.):\n"
        f"{case_context_json}\n\n"
        "Текущий PlantUML-код диаграммы:\n"
        "```plantuml\n"
        f"{plantuml}\n"
        "```\n\n"
        "Инструкции по изменениям (на русском):\n"
        f"{instructions}\n\n"
        "Сформируй НОВЫЙ PlantUML-код диаграммы, учитывая:\n"
        "- текущий PlantUML,\n"
        "- контекст кейса,\n"
        "- инструкции.\n\n"
        "В ответ верни ТОЛЬКО JSON, подходящий под schema из response_format, с полем \"plantuml\".\n"
    )


def apply_diagram_llm_edit(doc: GeneratedDocument, instructions: str) -> GeneratedDocument:
    """
    Правка диаграмм (BPMN / Context / UML Use Case) через GPT, с учётом контекста кейса.
    instructions — человеческий текст на русском, НЕ PlantUML.
    """
    instructions = (instructions or "").strip()
    if not instructions:
        raise ValueError("instructions is empty")

    if doc.doc_type not in (
        DocumentType.BPMN,
        DocumentType.CONTEXT_DIAGRAM,
        DocumentType.UML_USE_CASE_DIAGRAM,
    ):
        raise ValueError(f"apply_diagram_llm_edit: unsupported doc_type={doc.doc_type}")

    current_plantuml = _extract_current_plantuml(doc).strip()
    if not current_plantuml:
        current_plantuml = "@startuml\n@enduml"

    user_prompt = _build_user_prompt_for_diagram(doc, instructions, current_plantuml)

    data, _raw = chat_json(
        model=MODEL_NAME,
        system_prompt=SYSTEM_PROMPT_DIAGRAM_EDIT,
        user_prompt=user_prompt,
        response_format=RESPONSE_FORMAT_DIAGRAM_EDIT,
    )

    new_plantuml = (data.get("plantuml") or "").strip()
    if not new_plantuml:
        raise ValueError("LLM did not return plantuml field")

    if "@startuml" not in new_plantuml or "@enduml" not in new_plantuml:
        raise ValueError(
            "Неверный формат PlantUML: код должен содержать директивы '@startuml' и '@enduml'. "
            "Модель вернула некорректный код, попробуйте переформулировать инструкции."
        )

    structured = doc.structured_data or {}
    if not isinstance(structured, dict):
        structured = {}

    structured["plantuml"] = new_plantuml
    doc.structured_data = structured
    doc.content = f"```plantuml\n{new_plantuml}\n```"
    doc.updated_at = timezone.now()
    doc.save(update_fields=["structured_data", "content", "updated_at"])

    return doc

