from typing import Any, Dict, List


def _bullets(items: List[str]) -> str:
    return "\n".join([f"- {x}" for x in items]) if items else "- Требует уточнения на основании исходных данных"


def render(data: Dict[str, Any]) -> str:
    title = (data.get("title") or "").strip()
    problem = (data.get("problem_statement") or "").strip()

    return (
        "# Vision\n\n"
        f"## {title}\n\n"
        "### Problem statement\n"
        f"{problem}\n\n"
        "### Business goals\n"
        f"{_bullets(data.get('business_goals', []))}\n\n"
        "### Target users\n"
        f"{_bullets(data.get('target_users', []))}\n\n"
        "### Expected outcomes\n"
        f"{_bullets(data.get('expected_outcomes', []))}\n\n"
        "### Success criteria\n"
        f"{_bullets(data.get('success_criteria', []))}\n\n"
        "### Risks and limitations\n"
        f"{_bullets(data.get('risks_and_limitations', []))}\n"
    )
