from typing import Any, Dict


def render(structured: Dict[str, Any]) -> str:
    """
    Строим markdown-контент для UI / DOCX.

    - Вставляем PlantUML в блок ```plantuml
    - Ниже — список комментариев (если есть)
    """
    plantuml = (structured.get("plantuml") or "").strip()
    notes = structured.get("notes") or []

    parts: list[str] = []

    if plantuml:
        parts.append("```plantuml")
        parts.append(plantuml)
        parts.append("```")

    if notes:
        parts.append("")
        parts.append("**Комментарии к диаграмме:**")
        for n in notes:
            parts.append(f"- {n}")

    return "\n".join(parts).strip()