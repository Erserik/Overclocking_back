# documents/services/artifacts/context_diagram/schema.py

from typing import Any, Dict, List


def validate(raw: Any) -> Dict[str, Any]:
    """
    Минимальная валидация структуры ответа LLM для контекстной диаграммы.

    Ожидаем формат:
    {
      "plantuml": "...",
      "notes": ["...", "..."]
    }
    """

    if not isinstance(raw, dict):
        # если пришла строка — оборачиваем
        return {
            "plantuml": str(raw or ""),
            "notes": [],
        }

    plantuml = raw.get("plantuml") or raw.get("diagram") or ""
    if not isinstance(plantuml, str):
        plantuml = str(plantuml)

    notes_raw = raw.get("notes", [])
    notes: List[str] = []
    if isinstance(notes_raw, list):
        for n in notes_raw:
            if isinstance(n, str):
                notes.append(n)
            else:
                notes.append(str(n))
    elif isinstance(notes_raw, str):
        notes = [notes_raw]
    else:
        notes = [str(notes_raw)]

    # простая гарантия наличия @startuml/@enduml (если модель забыла)
    if plantuml and "@startuml" not in plantuml:
        plantuml = "@startuml\n" + plantuml.strip() + "\n@enduml"
    if plantuml and "@enduml" not in plantuml:
        plantuml = plantuml.strip() + "\n@enduml"

    return {
        "plantuml": plantuml,
        "notes": notes,
    }
