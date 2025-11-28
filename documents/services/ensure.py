# documents/services/ensure.py

import logging
from typing import Dict, List, Tuple

from django.db import transaction

from cases.models import Case
from documents.models import (
    GeneratedDocument,
    GenerationStatus,
    DocumentType,
    DocumentStatus,
)

from .context_builder import build_case_context, build_source_snapshot_hash
from .dispatcher import compute_prompt_hash, generate_structured_and_render
from .artifacts.vision import prompt as vision_prompt
from .artifacts.scope import prompt as scope_prompt
from .artifacts.bpmn import prompt as bpmn_prompt
from .artifacts.context_diagram import prompt as ctx_prompt  # 👈 ВАЖНО

logger = logging.getLogger(__name__)

# Теперь context_diagram тоже поддерживается
SUPPORTED_DOC_TYPES = {
    DocumentType.VISION,
    DocumentType.SCOPE,
    DocumentType.BPMN,
    DocumentType.CONTEXT_DIAGRAM,
}


def _artifact_prompts(doc_type: str, case_context: dict) -> Tuple[str, str, str]:
    """
    Возвращает (prompt_version, system_prompt, user_prompt)
    — нужно только для логирования/хэша промпта.
    """
    if doc_type == DocumentType.VISION:
        return (
            vision_prompt.PROMPT_VERSION,
            vision_prompt.SYSTEM_PROMPT,
            vision_prompt.build_user_prompt(case_context),
        )

    if doc_type == DocumentType.SCOPE:
        return (
            scope_prompt.PROMPT_VERSION,
            scope_prompt.SYSTEM_PROMPT,
            scope_prompt.build_user_prompt(case_context),
        )

    if doc_type == DocumentType.BPMN:
        return (
            bpmn_prompt.PROMPT_VERSION,
            bpmn_prompt.SYSTEM_PROMPT,
            bpmn_prompt.build_user_prompt(case_context),
        )

    if doc_type == DocumentType.CONTEXT_DIAGRAM:
        return (
            ctx_prompt.PROMPT_VERSION,
            ctx_prompt.SYSTEM_PROMPT,
            ctx_prompt.build_user_prompt(case_context),
        )

    # сюда больше попадать не должны
    raise ValueError(f"Unsupported doc_type: {doc_type}")


def ensure_case_documents(case: Case) -> Tuple[List[GeneratedDocument], Dict[str, str], bool]:
    """
    Ленивое создание документов:
    - Работает при любом статусе кейса.
    - Создаёт только те документы, у которых ещё нет structured_data.
    - Если selected_document_types пуст — по умолчанию VISION + SCOPE.
    """
    # например: ["vision", "scope", "context_diagram", "bpmn"]
    selected = case.selected_document_types or [DocumentType.VISION, DocumentType.SCOPE]
    # отфильтровали только те, которые реально поддерживаем
    target = [t for t in selected if t in SUPPORTED_DOC_TYPES]

    errors: Dict[str, str] = {}
    did_generate_any = False

    case_context = build_case_context(case)
    snapshot_hash = build_source_snapshot_hash(case)

    with transaction.atomic():
        locked_case = Case.objects.select_for_update().get(pk=case.pk)

        for doc_type in target:
            existing = GeneratedDocument.objects.filter(
                case=locked_case,
                doc_type=doc_type,
            ).first()

            # если уже есть structured_data — ничего не делаем
            if existing and existing.structured_data:
                continue

            try:
                # ставим статус GENERATING
                doc, _ = GeneratedDocument.objects.update_or_create(
                    case=locked_case,
                    doc_type=doc_type,
                    defaults={
                        "generation_status": GenerationStatus.GENERATING,
                        "error_message": None,
                        "status": DocumentStatus.DRAFT,
                        "title": f"{doc_type}: {locked_case.title}",
                        "content": "",
                        "structured_data": None,
                        "source_snapshot_hash": snapshot_hash,
                    },
                )

                # промпты — только чтобы посчитать хэш и сохранить версию
                prompt_version, system_prompt, user_prompt = _artifact_prompts(doc_type, case_context)
                p_hash = compute_prompt_hash(system_prompt, user_prompt)

                # основная магия — вызывает нужный генератор (vision/scope/bpmn/context)
                structured, content, title, used_model = generate_structured_and_render(
                    doc_type,
                    case_context,
                )

                doc.title = title
                doc.content = content
                doc.structured_data = structured
                doc.llm_model = used_model
                doc.prompt_version = prompt_version
                doc.prompt_hash = p_hash
                doc.source_snapshot_hash = snapshot_hash
                doc.generation_status = GenerationStatus.READY
                doc.error_message = None
                doc.save()

                did_generate_any = True

            except Exception as e:
                logger.exception("Failed ensuring doc_type=%s for case=%s", doc_type, locked_case.id)
                errors[doc_type] = str(e)
                GeneratedDocument.objects.filter(case=locked_case, doc_type=doc_type).update(
                    generation_status=GenerationStatus.FAILED,
                    error_message=str(e),
                )

    docs = list(GeneratedDocument.objects.filter(case=case).order_by("doc_type"))
    return docs, errors, did_generate_any
