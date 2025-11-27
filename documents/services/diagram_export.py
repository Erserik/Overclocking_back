from pathlib import Path
from typing import Optional

from django.conf import settings

from documents.models import GeneratedDocument, DocumentType
from .artifacts.bpmn.renderer import render_bpmn_image


def ensure_bpmn_image_for_case(case_id: str, plantuml_code: str) -> str:
    """
    Рендерит BPMN-диаграмму в PNG через PlantUML и кладёт в MEDIA_ROOT/generated_diagrams/.

    Возвращает относительный путь внутри MEDIA (например
    "generated_diagrams/49b0..._bpmn.png").
    """
    filename = f"{case_id}_bpmn.png"
    relative_path = Path("generated_diagrams") / filename
    full_path = Path(settings.MEDIA_ROOT) / relative_path

    # сам рендер картинки
    render_bpmn_image(plantuml_code, full_path)

    # важно: возвращаем строку, чтобы можно было сохранить в БД / отдать во фронт
    return str(relative_path)


def ensure_bpmn_image_for_document(doc: GeneratedDocument) -> Optional[str]:
    """
    Удобная обёртка: принимает GeneratedDocument и, если это BPMN-документ
    и в structured_data есть plantuml_code, рендерит PNG и возвращает относительный путь.

    Можно вызывать из POST /documents/ после ensure_case_documents.
    """
    if doc.doc_type != DocumentType.BPMN:
        return None

    data = doc.structured_data or {}
    plantuml_code = data.get("plantuml_code")
    if not plantuml_code:
        return None

    case_id = str(doc.case_id)
    relative_path = ensure_bpmn_image_for_case(case_id, plantuml_code)

    # Если у тебя в модели есть поле, где хранить путь — сохраняем.
    # Например, CharField: diagram_image_path = models.CharField(...)
    if hasattr(doc, "diagram_image_path"):
        doc.diagram_image_path = relative_path
        doc.save(update_fields=["diagram_image_path"])

    return relative_path
