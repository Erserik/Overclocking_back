from __future__ import annotations

import json
import logging
from typing import Any, Dict

from django.conf import settings

from documents.models import GeneratedDocument, DocumentType, GenerationStatus
from .llm_client import chat_json
from .artifacts.vision.renderer import render as render_vision
from .artifacts.scope.renderer import render as render_scope

logger = logging.getLogger(__name__)


def _build_edit_system_prompt(doc_type: str) -> str:
    base = """
Ты опытный бизнес-аналитик и редактор требований.
Тебе даётся уже существующий СТРУКТУРИРОВАННЫЙ документ (JSON),
который нужно АККУРАТНО изменить по инструкциям пользователя.

Главная цель:
- внести необходимые правки;
- СОХРАНИТЬ исходную структуру JSON (те же корневые поля и вложенные разделы);
- писать только на русском языке.

НЕЛЬЗЯ:
- выдумывать новые корневые поля;
- удалять важные разделы без явной причины;
- возвращать текст вне JSON.

Формат ответа СТРОГО:

{
  "structured": { ... изменённый JSON такого же формата ... }
}
""".strip()

    if doc_type == DocumentType.VISION:
        extra = "\nТип документа: Vision / Product Vision (цели продукта, ценность, пользователи, ограничения и т.п.)."
    elif doc_type == DocumentType.SCOPE:
        extra = "\nТип документа: Scope (границы решения, in_scope / out_of_scope, риски, зависимости, предположения)."
    else:
        extra = "\nТип документа: общий бизнес-документ."

    return (base + extra).strip()


def _build_edit_user_prompt(doc: GeneratedDocument, instructions: str) -> str:
    case = getattr(doc, "case", None)

    payload: Dict[str, Any] = {
        "doc_type": doc.doc_type,
        "case_id": str(getattr(case, "id", "")),
        "case_title": getattr(case, "title", ""),
        "current_title": doc.title,
        "current_structured": doc.structured_data or {},
        "instructions": instructions,
    }

    return (
        "Вот текущий структурированный документ и инструкции по его изменению.\n"
        "Сделай минимально необходимый набор правок, чтобы выполнить запрос пользователя.\n"
        "Структуру JSON нужно сохранить как можно ближе к исходной.\n\n"
        f"Данные:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def apply_llm_edit(doc: GeneratedDocument, instructions: str) -> GeneratedDocument:
    """
    Вносит правки в structured_data через GPT и пересобирает Markdown-контент.

    Сейчас поддерживаются только doc_type = vision / scope.
    """
    if doc.doc_type not in (DocumentType.VISION, DocumentType.SCOPE):
        raise ValueError("LLM-редактирование пока поддерживается только для документов Vision и Scope")

    system_prompt = _build_edit_system_prompt(doc.doc_type)
    user_prompt = _build_edit_user_prompt(doc, instructions)

    logger.info("LLM edit | doc_id=%s, doc_type=%s", doc.id, doc.doc_type)

    raw, used_model = chat_json(
        system_prompt,
        user_prompt,
        model=getattr(settings, "OPENAI_MODEL_SCOPE", settings.OPENAI_MODEL_VISION),
    )

    if not isinstance(raw, dict):
        raise ValueError("Ожидался JSON с полем 'structured'")

    new_structured = raw.get("structured")
    if not isinstance(new_structured, dict):
        raise ValueError("Поле 'structured' отсутствует или имеет неверный формат")

    case = getattr(doc, "case", None)
    case_title = getattr(case, "title", "") or "Без названия"

    # Рендерим контент теми же рендерами, что и при генерации
    if doc.doc_type == DocumentType.VISION:
        content = render_vision(new_structured)
        title = (
            new_structured.get("title")
            or doc.title
            or f"Vision: {case_title}"
        ).strip()
    else:  # SCOPE
        content = render_scope(new_structured)
        # Scope обычно фиксированно называется
        title = f"Scope: {case_title}"

    doc.structured_data = new_structured
    doc.content = content
    doc.title = title
    doc.llm_model = used_model
    doc.generation_status = GenerationStatus.READY
    doc.error_message = None

    doc.save(
        update_fields=[
            "structured_data",
            "content",
            "title",
            "llm_model",
            "generation_status",
            "error_message",
            "updated_at",
        ]
    )

    return doc
