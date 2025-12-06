from typing import Optional

from django.db.models import Max

from documents.models import GeneratedDocument, DocumentVersion


def get_next_version_number(document: GeneratedDocument) -> int:
    """
    Возвращает следующий номер версии документа.
    """
    latest = (
        DocumentVersion.objects
        .filter(document=document)
        .aggregate(max_ver=Max("version"))
        .get("max_ver")
    )
    if latest is None:
        return 1
    return latest + 1


def create_document_version_snapshot(
    document: GeneratedDocument,
    reason: Optional[str] = None,
) -> DocumentVersion:
    """
    Создаёт снэпшот текущего состояния документа как новую версию.
    """
    version_number = get_next_version_number(document)

    return DocumentVersion.objects.create(
        document=document,
        version=version_number,
        title=document.title,
        content=document.content,
        structured_data=document.structured_data,
        reason=reason,
    )