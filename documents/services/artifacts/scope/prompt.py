import json
from typing import Any, Dict

PROMPT_VERSION = "scope:v1"

SYSTEM_PROMPT = """
Ты опытный бизнес-аналитик крупного банка.
Сгенерируй черновик документа Scope (границы решения) по инициативе.

Требования:
- официальный деловой стиль;
- явно разделяй, что входит в рамки и что не входит;
- не придумывай технические детали; использовать только факты из входных данных;
- если информации не хватает — "Требует уточнения на основании исходных данных".

Формат ответа — строго JSON без пояснений и комментариев, строго по структуре:
{
  "summary": "",
  "in_scope": [""],
  "out_of_scope": [""],
  "business_processes_in_scope": [""],
  "systems_in_scope": [""],
  "assumptions": [""],
  "constraints": [""]
}
""".strip()


def build_user_prompt(case_context: Dict[str, Any]) -> str:
    payload = json.dumps(case_context, ensure_ascii=False, indent=2)
    return (
        "На основе данных ниже сгенерируй JSON для документа Scope (границы решения).\n"
        "Данные кейса и ответы:\n\n"
        f"{payload}"
    )
