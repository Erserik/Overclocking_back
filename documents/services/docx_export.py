from typing import Optional

from django.core.files.base import ContentFile
from django.utils import timezone

from documents.models import GeneratedDocument
from documents.models import DocumentType

from .artifacts.vision.docx import build_docx as build_vision_docx
from .artifacts.scope.docx import build_docx as build_scope_docx


def _build_docx_bytes_for_type(doc: GeneratedDocument) -> Optional[bytes]:
    """
    Делегируем сборку DOCX в конкретный артефакт.
    """
    if not doc.structured_data:
        return None

    if doc.doc_type == DocumentType.VISION:
        return build_vision_docx(doc.structured_data)

    if doc.doc_type == DocumentType.SCOPE:
        return build_scope_docx(doc.structured_data)

    # пока другие типы не поддерживаем
    return None


def ensure_docx_for_document(doc: GeneratedDocument, *, force: bool = False) -> GeneratedDocument:
    """
    Убедиться, что у документа есть docx_file.
    Если он уже есть и force=False — ничего не делаем.
    """
    if not doc.structured_data:
        # нечего экспортировать
        return doc

    if doc.docx_file and doc.docx_file.name and not force:
        return doc

    content_bytes = _build_docx_bytes_for_type(doc)
    if content_bytes is None:
        return doc  # неподдерживаемый тип

    if doc.doc_type == DocumentType.VISION:
        filename = f"{doc.case_id}_vision.docx"
    elif doc.doc_type == DocumentType.SCOPE:
        filename = f"{doc.case_id}_scope.docx"
    else:
        filename = f"{doc.case_id}_{doc.doc_type}.docx"

    doc.docx_file.save(filename, ContentFile(content_bytes), save=False)
    doc.docx_generated_at = timezone.now()
    doc.save(update_fields=["docx_file", "docx_generated_at", "updated_at"])
    return doc
