from typing import Any, Dict, Tuple

from documents.services.agent_client import run_usecase_agent


def generate(case_context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Генерация UML use case диаграммы через AI Agent Workflow.

    Ожидаем от воркфлоу структуру:
    {
      "plantuml": "@startuml ... @enduml",
      "notes": ["...", ...]
    }
    """
    resp = run_usecase_agent(case_context)

    plantuml = resp.get("plantuml", "") or ""
    notes = resp.get("notes") or []

    structured: Dict[str, Any] = {
        "plantuml": plantuml,
        "notes": notes,
    }

    used_model = "workflow_usecase_agent"
    return structured, used_model
