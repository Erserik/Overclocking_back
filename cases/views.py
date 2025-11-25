from rest_framework import generics
from .models import Case
from .serializers import (
    CaseSessionCreateSerializer,
    CaseInitialAnswersSerializer,
    CaseDetailSerializer,
)

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
)


@extend_schema(
    tags=['Cases'],
    summary='Создать кейс (сессию)',
    description=(
        'Шаг 1. Создаёт новый бизнес-кейс/сессию. '
        'На этом шаге пользователь указывает только название (title) '
        'и, опционально, своё имя. В ответ возвращается uid кейса.'
    ),
    request=CaseSessionCreateSerializer,
    responses={201: CaseSessionCreateSerializer},
    examples=[
        OpenApiExample(
            'Пример запроса',
            value={
                "title": "AI-агент бизнес-аналитик для продуктов Forte",
                "requester_name": "Иван Иванов",
            },
            request_only=True,
        ),
    ],
)
class CaseSessionCreateView(generics.CreateAPIView):
    """
    POST /api/cases/
    """
    queryset = Case.objects.all()
    serializer_class = CaseSessionCreateSerializer


@extend_schema(
    tags=['Cases'],
    summary='Сохранить ответы на 8 стартовых вопросов',
    description=(
        'Шаг 2. Обновляет уже созданный кейс, добавляя ответы на 8 '
        'стартовых вопросов (initial_answers) и список типов документов '
        '(selected_document_types). После этого статус кейса меняется '
        'на "in_progress".'
    ),
    request=CaseInitialAnswersSerializer,
    responses={200: CaseDetailSerializer},
    examples=[
        OpenApiExample(
            'Пример запроса',
            value={
                "initial_answers": {
                    "idea": "AI-агент бизнес-аналитик для внутренних запросов.",
                    "target_users": "Сотрудники банка, инициирующие изменения.",
                    "problem": "BA тратят много времени на первичный сбор информации.",
                    "ideal_flow": "1) Пользователь отвечает на вопросы, 2) AI генерит документы.",
                    "user_actions": "Создавать кейс, отвечать на вопросы, получать документы.",
                    "mvp": "Сбор требований и генерация BRD + Use Case.",
                    "constraints": "Интеграция с текущими системами, требования по безопасности.",
                    "success_criteria": "Сократить время BA на первичный бриф на 50%."
                },
                "selected_document_types": ["vision", "use_case"]
            },
            request_only=True,
        ),
    ],
)
class CaseInitialAnswersUpdateView(generics.UpdateAPIView):
    """
    PUT /api/cases/{id}/initial-answers/
    """
    queryset = Case.objects.all()
    serializer_class = CaseInitialAnswersSerializer
    lookup_field = "pk"
    http_method_names = ['put', 'options', 'head']


@extend_schema(
    tags=['Cases'],
    summary='Получить информацию о кейсе',
    description=(
        'Возвращает детальную информацию по кейсу: название, статус, инициатора, '
        'ответы на стартовые вопросы (если уже заполнены) и выбранные типы документов.'
    ),
    responses={200: CaseDetailSerializer},
)
class CaseDetailView(generics.RetrieveAPIView):
    """
    GET /api/cases/{id}/
    """
    queryset = Case.objects.all()
    serializer_class = CaseDetailSerializer
    lookup_field = "pk"
