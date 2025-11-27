import json
from typing import Any, Dict

PROMPT_VERSION = "vision:v1"

SYSTEM_PROMPT = """
Ты опытный бизнес-аналитик крупного банка.
Сгенерируй черновик документа Vision / Problem Statement по инициативе.

Требования:
- официальный деловой стиль, без воды;
- язык: русский;
- использовать только факты из входных данных, не придумывать технические детали;
- если информации не хватает, заполняй нейтрально: "Требует уточнения на основании исходных данных".

Формат ответа — строго JSON без пояснений и комментариев, строго по структуре:
{
  "title": "",
  "problem_statement": "",
  "business_goals": [""],
  "target_users": [""],
  "expected_outcomes": [""],
  "success_criteria": [""],
  "risks_and_limitations": [""]
}
""".strip()


def build_user_prompt(case_context: Dict[str, Any]) -> str:
    payload = json.dumps(case_context, ensure_ascii=False, indent=2)
    return (
        "На основе данных ниже сгенерируй JSON для документа Vision.\n"
        "Данные кейса и ответы:\n\n"
        f"{payload}"
    )
