from typing import Any, Dict, Tuple

from documents.models import DocumentType
from .utils import sha256_text

# ------- VISION -------
from .artifacts.vision import prompt as vision_prompt
from .artifacts.vision.generator import generate as generate_vision
from .artifacts.vision.renderer import render as render_vision

# ------- SCOPE -------
from .artifacts.scope import prompt as scope_prompt
from .artifacts.scope.generator import generate as generate_scope
from .artifacts.scope.renderer import render as render_scope

# ------- BPMN -------
from .artifacts.bpmn import prompt as bpmn_prompt
from .artifacts.bpmn.generator import generate as generate_bpmn
from .artifacts.bpmn.renderer import render as render_bpmn

# ------- CONTEXT DIAGRAM -------
from .artifacts.context_diagram import prompt as ctx_prompt
from .artifacts.context_diagram.generator import generate as generate_context
from .artifacts.context_diagram.renderer import render as render_context


def get_artifact_prompt_bundle(doc_type: str) -> Tuple[str, str, str]:
    """
    Возвращает: (prompt_version, system_prompt, template_hash_source)
    Если где-то нужно получить базовый набор промптов по типу документа.
    """
    if doc_type == DocumentType.VISION:
        return vision_prompt.PROMPT_VERSION, vision_prompt.SYSTEM_PROMPT, "vision"

    if doc_type == DocumentType.SCOPE:
        return scope_prompt.PROMPT_VERSION, scope_prompt.SYSTEM_PROMPT, "scope"

    if doc_type == DocumentType.BPMN:
        # Для BPMN используем свой system prompt
        return bpmn_prompt.PROMPT_VERSION, bpmn_prompt.SYSTEM_PROMPT, "bpmn"

    if doc_type == DocumentType.CONTEXT_DIAGRAM:
        return ctx_prompt.PROMPT_VERSION, ctx_prompt.SYSTEM_PROMPT, "context_diagram"

    if doc_type == DocumentType.UML_USE_CASE_DIAGRAM:
        # Пока без отдельного промпта — просто метки
        return "uml_use_case_v1", "UML USE CASE FALLBACK", "uml_use_case"

    raise ValueError(f"Unsupported doc_type: {doc_type}")


def compute_prompt_hash(system_prompt: str, user_prompt: str) -> str:
    """
    Хешируем фактические строковые промпты (system + user),
    чтобы понимать, когда документ устарел.
    """
    return sha256_text(system_prompt + "\n---\n" + user_prompt)


def generate_structured_and_render(
    doc_type: str,
    case_context: Dict[str, Any],
) -> Tuple[Dict[str, Any], str, str, str]:
    """
    Главный диспетчер генерации артефактов.

    Возвращает кортеж:
    - structured_data: Dict[str, Any] — то, что кладём в structured_data
    - content_md: str — markdown/текст, который показываем в UI и конвертим в DOCX
    - title: str — заголовок документа
    - used_model: str — имя LLM-модели (для логирования/аудита)
    """

    # ---------- VISION ----------
    if doc_type == DocumentType.VISION:
        structured, used_model = generate_vision(case_context)
        content = render_vision(structured)
        title = (
            structured.get("title")
            or case_context["case"]["title"]
        )
        title = (title or "").strip() or case_context["case"]["title"]
        return structured, content, title, used_model

    # ---------- SCOPE ----------
    if doc_type == DocumentType.SCOPE:
        structured, used_model = generate_scope(case_context)
        content = render_scope(structured)
        title = f"Scope: {case_context['case']['title']}"
        return structured, content, title, used_model

    # ---------- BPMN ----------
    if doc_type == DocumentType.BPMN:
        structured, used_model = generate_bpmn(case_context)
        # render_bpmn обычно формирует markdown с ```plantuml``` блоком
        content = render_bpmn(structured)
        title = f"BPMN: {case_context['case']['title']}"
        return structured, content, title, used_model

    # ---------- CONTEXT DIAGRAM ----------
    if doc_type == DocumentType.CONTEXT_DIAGRAM:
        structured, used_model = generate_context(case_context)
        # renderer формирует понятный текст + ```plantuml``` с контекстной диаграммой
        content = render_context(structured)
        title = f"Context: {case_context['case']['title']}"
        return structured, content, title, used_model

    # ---------- UML USE CASE DIAGRAM (простая заглушка без GPT) ----------
    if doc_type == DocumentType.UML_USE_CASE_DIAGRAM:
        case_title = case_context.get("case", {}).get("title", "Без названия")

        initial_answers = (
            case_context.get("case", {}).get("initial_answers")
            or {}
        )
        idea = (initial_answers.get("idea") or "").strip()
        user_actions = (initial_answers.get("user_actions") or "").strip()

        plantuml = f"""@startuml
title Use Case: {case_title}

actor "Пользователь" as User
actor "Бизнес-аналитик" as BA

rectangle "{case_title}" as System {{
  usecase "Основной сценарий" as UC_Main
  usecase "Просмотр отчётов" as UC_Reports
}}

User --> UC_Main
BA --> UC_Reports

@enduml
"""

        structured: Dict[str, Any] = {
            "plantuml": plantuml,
            "notes": [
                "Черновая UML use case диаграмма на основе базовых ответов.",
                f"Идея: {idea[:120]}",
                f"Действия пользователя: {user_actions[:120]}",
            ],
        }

        content_md = f"```plantuml\n{plantuml}\n```"
        title = f"Use Case: {case_title}"
        used_model = "static_fallback_uml_use_case"

        return structured, content_md, title, used_model

    # Если забыли добавить новый тип — валимся сюда
    raise ValueError("Unsupported doc_type")
