from typing import Any, Dict, List


def _bullets(items: List[str]) -> str:
    return "\n".join([f"- {x}" for x in items]) if items else "- Требует уточнения на основании исходных данных"


def render(data: Dict[str, Any]) -> str:
    summary = (data.get("summary") or "").strip() or "Требует уточнения на основании исходных данных"

    return (
        "# Scope\n\n"
        "## Summary\n"
        f"{summary}\n\n"
        "## In vision\n"
        f"{_bullets(data.get('in_scope', []))}\n\n"
        "## Out of vision\n"
        f"{_bullets(data.get('out_of_scope', []))}\n\n"
        "## Business processes in vision\n"
        f"{_bullets(data.get('business_processes_in_scope', []))}\n\n"
        "## Systems in vision\n"
        f"{_bullets(data.get('systems_in_scope', []))}\n\n"
        "## Assumptions\n"
        f"{_bullets(data.get('assumptions', []))}\n\n"
        "## Constraints\n"
        f"{_bullets(data.get('constraints', []))}\n"
    )
