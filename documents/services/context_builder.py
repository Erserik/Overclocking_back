from typing import Any, Dict, List

from cases.models import Case, FollowupQuestionStatus
from .utils import sha256_json


def build_case_context(case: Case) -> Dict[str, Any]:
    followups = case.followup_questions.filter(
        status=FollowupQuestionStatus.ANSWERED
    ).order_by("order_index")

    followup_block: List[Dict[str, Any]] = []
    for q in followups:
        followup_block.append(
            {
                "order_index": q.order_index,
                "code": q.code,
                "text": q.text,
                "answer": q.answer_text,
                "target_document_types": q.target_document_types or [],
            }
        )

    payload = {
        "case": {
            "id": str(case.id),
            "title": case.title,
            "status": case.status,
            "initial_answers": case.initial_answers,
            "selected_document_types": case.selected_document_types or [],
        },
        "followup_answers": followup_block,
    }
    return payload


def build_source_snapshot_hash(case: Case) -> str:
    return sha256_json(build_case_context(case))
