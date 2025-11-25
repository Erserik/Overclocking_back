# cases/services/followup.py

import json
import logging
import os
from typing import List, Dict, Any

from openai import OpenAI

from cases.models import Case, FollowupQuestion, FollowupQuestionStatus

logger = logging.getLogger(__name__)

# Модель по умолчанию — дешевая и быстрая
DEFAULT_GPT_MODEL = os.environ.get("GPT_MODEL_NAME", "gpt-4.1-mini")


def _build_case_context(case: Case) -> str:
    """
    Собираем человекочитаемый контекст кейса для промпта.
    """
    initial = case.initial_answers or {}

    def get(key: str) -> str:
        v = initial.get(key, "")
        return v if isinstance(v, str) else ""

    parts = [
        f"Название кейса: {case.title}",
        "",
        "Базовые ответы на 8 стартовых вопросов:",
        f"- Идея: {get('idea')}",
        f"- Целевая аудитория: {get('target_users')}",
        f"- Проблема: {get('problem')}",
        f"- Идеальный процесс: {get('ideal_flow')}",
        f"- Действия пользователя в системе: {get('user_actions')}",
        f"- MVP (что обязательно в первой версии): {get('mvp')}",
        f"- Ограничения и риски: {get('constraints')}",
        f"- Критерии успеха: {get('success_criteria')}",
        "",
        "Сырые ответы (JSON):",
        json.dumps(initial, ensure_ascii=False, indent=2),
    ]

    doc_types = case.selected_document_types or []
    if doc_types:
        parts.append("")
        parts.append(
            f"Пользователь хочет получить следующие типы документов: {doc_types}"
        )

    return "\n".join(parts)


def _fallback_questions(case: Case) -> List[Dict[str, Any]]:
    """
    Fallback, если GPT недоступен или вернул некорректный ответ.
    Простейший набор вопросов на основе выбранных типов документов.
    """
    doc_types = case.selected_document_types or []

    questions_def: List[Dict[str, Any]] = []

    questions_def.append(
        {
            "code": "roles",
            "text": (
                "Какие ключевые роли пользователей будут работать с системой "
                "(например, продакт, риск-аналитик, операционный сотрудник)?"
            ),
            "target_document_types": doc_types,
        }
    )

    if "vision" in doc_types:
        questions_def.append(
            {
                "code": "non_functional",
                "text": (
                    "Какие ключевые нефункциональные требования важны для решения "
                    "(производительность, доступность, аудит действий и т.п.)?"
                ),
                "target_document_types": ["vision"],
            }
        )

    if "use_case" in doc_types:
        questions_def.append(
            {
                "code": "main_use_case",
                "text": (
                    "Опишите, пожалуйста, основной сценарий: какие шаги проходит "
                    "инициатор от создания запроса до получения результата?"
                ),
                "target_document_types": ["use_case"],
            }
        )

    return questions_def


def generate_followup_questions_for_case(case: Case) -> List[FollowupQuestion]:
    """
    Генерирует план уточняющих вопросов для кейса с помощью GPT.

    Алгоритм:
    1. Удаляем старые follow-up вопросы для кейса.
    2. Формируем промпт на основе title, 8 ответов и типов документов.
    3. Вызываем GPT (gpt-4.1-mini), просим вернуть строго JSON с полем questions[].
    4. Валидируем ответ и создаём FollowupQuestion в БД.
    5. Если что-то пошло не так — используем fallback-вопросы.
    """

    # Чистим прошлый план вопросов
    case.followup_questions.all().delete()

    # Если нет initial_answers — генерировать нечего
    if not case.initial_answers:
        logger.warning(
            "generate_followup_questions_for_case: case %s has no initial_answers",
            case.id,
        )
        return []

    client = OpenAI()

    system_prompt = (
        "Ты опытный бизнес-аналитик в крупном банке. "
        "На входе у тебя есть краткий бриф по инициативе (ответы на 8 стартовых вопросов) "
        "и список типов аналитических документов, которые нужно подготовить "
        "(например, Vision/BRD, Use Case). "
        "Твоя задача — составить список уточняющих вопросов, которые нужно задать инициатору, "
        "чтобы подготовить эти документы с хорошим уровнем детализации.\n\n"
        "Требования к вопросам:\n"
        "- не повторяй базовые 8 вопросов, которые уже заданы в брифе;\n"
        "- задавай только те вопросы, которые реально помогают уточнить требования;\n"
        "- учитывай список типов документов: для Vision/BRD нужны более high-level вопросы, "
        "для Use Case — вопросы про сценарии, шаги, альтернативы и исключения;\n"
        "- максимум 10 вопросов;\n"
        "- формулируй вопросы на русском языке, деловым, но понятным тоном;\n"
        "- для каждого вопроса укажи:\n"
        "  * code — короткий идентификатор на английском (snake_case, без пробелов),\n"
        "  * text — текст вопроса на русском,\n"
        "  * target_document_types — список документов, для которых этот вопрос важен "
        "(подмножество входного списка типов документов).\n\n"
        "Верни ответ строго в формате JSON-объекта без пояснений и текста вокруг:\n"
        "{\n"
        '  \"questions\": [\n'
        "    {\n"
        '      \"code\": \"roles\",\n'
        '      \"text\": \"Какие ключевые роли пользователей будут работать с системой?\",\n'
        '      \"target_document_types\": [\"vision\", \"use_case\"]\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )

    user_prompt = _build_case_context(case)

    questions_def: List[Dict[str, Any]] = []

    try:
        response = client.chat.completions.create(
            model=DEFAULT_GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Вот данные по кейсу и стартовым ответам. "
                        "На их основе сгенерируй список уточняющих вопросов в формате, "
                        "описанном в инструкции выше.\n\n"
                        f"{user_prompt}"
                    ),
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        raw_questions = data.get("questions", [])
        if not isinstance(raw_questions, list):
            raise ValueError("field 'questions' is not a list")

        # Простейшая валидация и нормализация
        for idx, q in enumerate(raw_questions):
            if not isinstance(q, dict):
                continue

            text = q.get("text")
            if not isinstance(text, str) or not text.strip():
                continue

            code = q.get("code")
            if not isinstance(code, str) or not code.strip():
                code = f"q_{idx + 1}"

            tgt = q.get("target_document_types") or []
            if not isinstance(tgt, list):
                tgt = []
            # оставляем только строки
            tgt = [t for t in tgt if isinstance(t, str)]
            # если GPT не указал или указал ерунду — применяем все типы кейса
            if not tgt:
                tgt = case.selected_document_types or []

            questions_def.append(
                {
                    "code": code,
                    "text": text.strip(),
                    "target_document_types": tgt,
                }
            )

    except Exception as e:
        logger.exception("Error while calling GPT for follow-up questions: %s", e)

    # Если GPT ничего полезного не вернул — fallback
    if not questions_def:
        logger.warning(
            "GPT returned no valid follow-up questions for case %s, using fallback",
            case.id,
        )
        questions_def = _fallback_questions(case)

    # Если даже fallback пустой — выходим
    if not questions_def:
        return []

    # Создаём вопросы в БД
    created_questions: List[FollowupQuestion] = []

    for index, q in enumerate(questions_def):
        fq = FollowupQuestion.objects.create(
            case=case,
            order_index=index,
            code=q.get("code"),
            text=q["text"],
            target_document_types=q.get("target_document_types") or [],
            status=FollowupQuestionStatus.PENDING,
        )
        created_questions.append(fq)

    logger.info(
        "Generated %d follow-up questions for case %s",
        len(created_questions),
        case.id,
    )

    return created_questions
