# cases/services/followup.py

from typing import List, Dict

from cases.models import Case, FollowupQuestion, FollowupQuestionStatus


def generate_followup_questions_for_case(case: Case) -> List[FollowupQuestion]:
    """
    Заглушка генерации плана уточняющих вопросов.
    Сейчас: создаём несколько демонстрационных вопросов.
    Далее здесь можно подключить GPT, который вернёт JSON с вопросами.

    Правило: сначала очищаем старые follow-up вопросы для кейса,
    потом создаём новый список.
    """

    # Удаляем старые вопросы, если уже были
    case.followup_questions.all().delete()

    questions_def: List[Dict] = []

    # Простая логика заглушки: на основе выбранных типов документов
    doc_types = case.selected_document_types or []

    # Базовый вопрос — всегда
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

    # Если выбран vision
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

    # Если выбран use_case
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

    return created_questions
