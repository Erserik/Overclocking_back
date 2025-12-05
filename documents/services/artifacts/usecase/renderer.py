from typing import Any, Dict


def render(structured: Dict[str, Any]) -> str:
    """
    Рендерим Markdown с блоком ```plantuml``` + заметки.
    """
    plantuml = structured.get("plantuml", "") or ""
    notes = structured.get("notes") or []

    lines: list[str] = []

    if notes:
        lines.append("### Комментарии к диаграмме\n")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")  # пустая строка

    lines.append("```plantuml")
    lines.append(plantuml.strip())
    lines.append("```")

    return "\n".join(lines)
