from typing import Dict, Any

def validate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Минимальная валидация + зачистка опасных строк.
    Никакой сложной логики, главное — не потерять plantuml.
    """
    if not isinstance(raw, dict):
        raise ValueError("BPMN: raw response must be a JSON object")

    plantuml = raw.get("plantuml") or ""
    notes = raw.get("notes") or []

    if not isinstance(plantuml, str):
        raise ValueError("BPMN: 'plantuml' must be a string")
    if not isinstance(notes, list):
        notes = [str(notes)]

    # простая зачистка на всякий случай
    safe_lines = []
    for line in plantuml.splitlines():
        stripped = line.lstrip()
        # вырезаем заведомо запрещённые конструкции
        if stripped.startswith(("!include", "POOL", "LANE", "[")):
            continue
        safe_lines.append(line)

    plantuml = "\n".join(safe_lines).strip()

    # гарантируем @startuml / @enduml
    if not plantuml.startswith("@startuml"):
        plantuml = "@startuml\n" + plantuml
    if not plantuml.endswith("@enduml"):
        plantuml = plantuml + "\n@enduml"

    return {
        "plantuml": plantuml,
        "notes": notes,
    }
