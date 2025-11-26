import json
import logging
from typing import List, Dict

from openai import OpenAI

from cases.models import Case, FollowupQuestionStatus
from .models import GeneratedDocument, DocumentStatus

logger = logging.getLogger(__name__)

client = OpenAI()


def generate_documents_for_case(case: Case) -> List[GeneratedDocument]:
    """
    Генерирует документы для кейса с помощью GPT.

    Берём:
      - initial_answers (8 вопросов),
      - все followup_questions со статусом ANSWERED,
      - selected_document_types.

    GPT должен вернуть JSON формата:
    {
      "vision": {"title": "...", "content": "..."},
      "use_case": {"title": "...", "content": "..."}
    }
    """

    if not case.initial_answers:
        raise ValueError("Case has no initial_answers")

    doc_types = case.selected_document_types or []
    if not doc_types:
        logger.warning("Case %s has no selected_document_types", case.id)
        return []

    # собираем ответы на уточняющие вопросы
    followups = case.followup_questions.filter(
        status=FollowupQuestionStatus.ANSWERED
    ).order_by("order_index")

    followup_block = []
    for q in followups:
        followup_block.append(
            {
                "code": q.code,
                "text": q.text,
                "answer": q.answer_text,
                "target_document_types": q.target_document_types,
            }
        )

    system_prompt = (
        "Ты опытный бизнес-аналитик в крупном банке. "
        "На основе краткого брифа по инициативе и уточняющих ответов "
        "тебе нужно подготовить аналитические документы.\n\n"
        f"Документы, которые нужно подготовить: {doc_types}.\n\n"
        "Требования к ответу:\n"
        "- верни ОДИН JSON-объект без пояснений и текста вокруг;\n"
        "- для каждого типа документа верни объект с полями 'title' и 'content';\n"
        "- content пиши на русском, структурируй заголовками и списками (Markdown)."
    )

    user_payload = {
        "case": {
            "id": str(case.id),
            "title": case.title,
            "initial_answers": case.initial_answers,
            "selected_document_types": doc_types,
        },
        "followup_answers": followup_block,
    }

    user_prompt = (
        "Вот данные по кейсу, стартовым ответам и уточняющим ответам.\n"
        "На их основе сгенерируй документы.\n\n"
        + json.dumps(user_payload, ensure_ascii=False, indent=2)
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)
    except Exception as e:
        logger.exception("Error while calling GPT for documents for case %s: %s", case.id, e)
        return []

    created_docs: List[GeneratedDocument] = []

    # обходим запрошенные типы: vision, use_case, ...
    for doc_type in doc_types:
        doc_data: Dict = data.get(doc_type)
        if not isinstance(doc_data, dict):
            logger.warning("No document data for type %s in GPT response", doc_type)
            continue

        title = doc_data.get("title") or f"{doc_type} for {case.title}"
        content_text = doc_data.get("content")
        if not content_text:
            logger.warning("Empty content for doc_type %s", doc_type)
            continue

        # удаляем старый документ этого типа, если был
        GeneratedDocument.objects.filter(case=case, doc_type=doc_type).delete()

        doc = GeneratedDocument.objects.create(
            case=case,
            doc_type=doc_type,
            title=title,
            content=content_text,
            status=DocumentStatus.DRAFT,
            llm_model="gpt-4.1-mini",
        )
        created_docs.append(doc)

    return created_docs
