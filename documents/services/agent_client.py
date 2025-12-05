from __future__ import annotations

import json
import logging
from typing import Any, Dict

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


AgentClient = OpenAI


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
