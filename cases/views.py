from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from .models import Case, FollowupQuestion, FollowupQuestionStatus, CaseStatus
from .serializers import (
    CaseSessionCreateSerializer,
    CaseInitialAnswersSerializer,
    CaseDetailSerializer,
    NextQuestionResponseSerializer,
    AnswerQuestionSerializer,
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
                "requester_name": "Айгуль Садыкова",
            },
            request_only=True,
        ),
    ],
)
class CaseSessionCreateView(generics.ListCreateAPIView):
    """
    GET  /api/cases/   — список кейсов (для BA/админки)
    POST /api/cases/   — создать новый кейс (сессию)
    """
    queryset = Case.objects.all().order_by("-created_at")
    serializer_class = CaseSessionCreateSerializer



@extend_schema(
    tags=['Cases'],
    summary='Сохранить ответы на 8 стартовых вопросов',
    description=(
        'Шаг 2. Обновляет уже созданный кейс, добавляя ответы на 8 '
        'стартовых вопросов (initial_answers) и список типов документов '
        '(selected_document_types). После этого статус кейса меняется '
        'на "in_progress" и генерируется план уточняющих вопросов.'
    ),
    request=CaseInitialAnswersSerializer,
    responses={200: CaseDetailSerializer},
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


@extend_schema(
    tags=['Follow-up Questions'],
    summary='Получить следующий уточняющий вопрос по кейсу',
    description=(
        'Возвращает первый по порядку неотвеченный уточняющий вопрос '
        'для указанного кейса. Если все вопросы уже отвечены или вопросов нет, '
        'возвращает is_finished = true и переводит кейс в статус '
        '"ready_for_documents".'
    ),
    responses={200: NextQuestionResponseSerializer},
)
class NextFollowupQuestionView(generics.GenericAPIView):
    """
    GET /api/cases/{id}/next-question/
    """
    serializer_class = NextQuestionResponseSerializer

    def get(self, request, pk, *args, **kwargs):
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        all_questions = case.followup_questions.all()
        total_questions = all_questions.count()

        next_question = all_questions.filter(
            status=FollowupQuestionStatus.PENDING
        ).order_by("order_index").first()

        if next_question is None:
            # нет ни одного ожидающего вопроса
            # считаем, что кейс готов к генерации документов
            if case.status == CaseStatus.IN_PROGRESS:
                case.status = CaseStatus.READY_FOR_DOCUMENTS
                case.save(update_fields=["status"])

            data = {
                "question_id": None,
                "order_index": None,
                "total_questions": total_questions,
                "text": None,
                "target_document_types": [],
                "is_finished": True,
            }
        else:
            data = {
                "question_id": next_question.id,
                "order_index": next_question.order_index,
                "total_questions": total_questions,
                "text": next_question.text,
                "target_document_types": next_question.target_document_types or [],
                "is_finished": False,
            }

        serializer = self.get_serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Follow-up Questions'],
    summary='Ответить на уточняющий вопрос по кейсу',
    description=(
        'Сохраняет ответ пользователя на конкретный уточняющий вопрос и '
        'помечает его как "answered". После этого можно запрашивать следующий вопрос.'
    ),
    request=AnswerQuestionSerializer,
    responses={200: None},
    examples=[
        OpenApiExample(
            'Пример запроса',
            value={
                "question_id": "11111111-2222-3333-4444-555555555555",
                "answer": (
                    "Основные роли: бизнес-заказчик (продакт), риск-аналитик, "
                    "бизнес-архитектор и специалист ИТ-поддержки."
                ),
            },
            request_only=True,
        ),
    ],
)
class AnswerFollowupQuestionView(generics.GenericAPIView):
    """
    POST /api/cases/{id}/answer-question/
    """
    serializer_class = AnswerQuestionSerializer

    def post(self, request, pk, *args, **kwargs):
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data["question_id"]
        answer = serializer.validated_data["answer"]

        try:
            question = case.followup_questions.get(pk=question_id)
        except FollowupQuestion.DoesNotExist:
            raise ValidationError("Question does not belong to this case or not found")

        question.answer_text = answer
        question.status = FollowupQuestionStatus.ANSWERED
        question.save(update_fields=["answer_text", "status"])

        return Response(status=status.HTTP_200_OK)
