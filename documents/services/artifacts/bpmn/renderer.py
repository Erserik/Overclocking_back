from pathlib import Path
from typing import Dict, Any, Tuple

import requests
from django.conf import settings

from . import prompt, schema


def _call_plantuml_server(plantuml_code: str) -> bytes:
    """
    Отправляем PlantUML-код на сервер и получаем PNG-байты.

    Используем POST без компрессии (так проще),
    сервер https://www.plantuml.com/plantuml/png это понимает.
    """
    url = settings.PLANTUML_SERVER_URL.rstrip("/")

    resp = requests.post(
        url,
        data=plantuml_code.encode("utf-8"),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.content


def render_bpmn_image(plantuml_code: str, output_path: Path) -> None:
    """
    Рендерит PNG через PlantUML-сервер и сохраняет в output_path.
    """
    png_bytes = _call_plantuml_server(plantuml_code)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(png_bytes)


def render(structured_data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Главный рендерер BPMN-артефакта.

    Возвращает:
      - markdown_summary: краткое текстовое описание диаграммы (чтобы было что показывать в UI/доках)
      - plantuml_code: исходный PlantUML-код (он же идёт в structured_data)

    Сам PNG мы генерим отдельным шагом (в docx_export / ensure_diagram_image).
    """
    # structured_data мы получили уже после schema.validate(...)
    title = structured_data.get("title") or "BPMN Diagram"
    description = structured_data.get("description") or ""

    plantuml_code = structured_data.get("plantuml_code") or ""

    # На всякий случай: если GPT не вернул PlantUML — делаем примитивную заглушку,
    # но уже корректную с точки зрения PlantUML (чтобы сервер не падал).
    if not plantuml_code.strip():
        plantuml_code = f"""@startuml
title {title}
note as N
GPT не вернул полноценный BPMN-код, отображается заглушка.
end note
@enduml
"""

    # Текстовое summary, которое мы сохраняем в GeneratedDocument.content
    markdown_summary = f"# BPMN: {title}\n\n" \
                       f"Generated from GPT (PlantUML).\n\n" \
                       f"{description}\n"

    return markdown_summary, plantuml_code
