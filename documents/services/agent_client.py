from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

# Просто alias, чтобы при желании можно было подменять
AgentClient = OpenAI


# ========= 1. Вызов workflow (AI Agent) =========

def run_workflow(
    workflow_id: str,
    input_data: Dict[str, Any],
    *,
    model: str | None = None,
) -> Dict[str, Any]:
    """
    Вызов OpenAI Workflow (AI Agent) по ID.
    """
    client = AgentClient()

    used_model = model or getattr(
        settings,
        "OPENAI_AGENT_MODEL",
        "gpt-5.1-mini",
    )

    logger.info(
        "Calling workflow %s with model=%s and input keys=%s",
        workflow_id,
        used_model,
        list(input_data.keys()),
    )

    run = client.workflows.runs.create(
        workflow_id=workflow_id,
        input=input_data,
        model=used_model,
    )

    output = getattr(run, "output", None) or {}

    try:
        logger.info(
            "Workflow %s finished. Output keys=%s, raw_output=%s",
            workflow_id,
            list(output.keys()),
            json.dumps(output, ensure_ascii=False)[:1000],
        )
    except Exception:
        logger.exception("Failed to log workflow output for %s", workflow_id)

    return output


def run_usecase_agent(case_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Специальный вызов воркфлоу для use case диаграммы.
    """
    workflow_id = getattr(settings, "OPENAI_USECASE_WORKFLOW_ID", None)
    if not workflow_id:
        raise RuntimeError("OPENAI_USECASE_WORKFLOW_ID is not configured in settings")

    input_payload = {
        "case_context": case_context,
    }

    return run_workflow(
        workflow_id=workflow_id,
        input_data=input_payload,
    )


# ========= 2. Обычный chat-completion с JSON-ответом =========

def chat_json(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_format: Dict[str, Any],
) -> Tuple[Dict[str, Any], str]:
    """
    Вызов GPT, который должен вернуть JSON по заданной json_schema.

    Параметры:
      - model: имя модели (например, "gpt-5.1" или "gpt-5.1-mini")
      - system_prompt: системный промпт
      - user_prompt: промпт пользователя
      - response_format: dict с json_schema (как в DIAGRAM_EDIT)

    Возвращает:
      - data: dict, распарсенный JSON из ответа модели
      - raw: str, сырой текст ответа (для логов/отладки)
    """
    client = AgentClient()

    logger.info(
        "Calling chat_json with model=%s, response_format=%s",
        model,
        response_format.get("type"),
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_format,
    )

    raw = completion.choices[0].message.content or ""

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON from LLM response")
        raise ValueError(
            f"LLM returned non-JSON response. Raw content:\n{raw}"
        )

    if not isinstance(data, dict):
        raise ValueError(
            f"LLM JSON response is not an object. Raw content:\n{raw}"
        )

    return data, raw