# documents/services/artifacts/context_diagram/renderer.py

from typing import Any, Dict, List


def render(structured: Dict[str, Any]) -> str:
    """
    Рендер контекстной диаграммы в markdown:
    - заголовок
    - краткие заметки
    - блок с ```plantuml```.
    """

    plantuml: str = (structured or {}).get("plantuml", "") or ""
    notes: List[str] = (structured or {}).get("notes", []) or []

    lines: List[str] = []
    lines.append("# Context Diagram")
    lines.append("")
    if notes:
        lines.append("## Краткие комментарии")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")

    lines.append("## Диаграмма (PlantUML)")
    lines.append("")
    lines.append("```plantuml")
    lines.append(plantuml.strip())
    lines.append("```")
    lines.append("")

    return "\n".join(lines)
