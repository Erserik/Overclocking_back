from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
)

from .models import Case, FollowupQuestion, FollowupQuestionStatus, CaseStatus
from .serializers import (
    CaseSessionCreateSerializer,
    CaseInitialAnswersSerializer,
    CaseDetailSerializer,
    NextQuestionResponseSerializer,
    AnswerQuestionSerializer,
)


# ======================= Роли (AUTHORITY / ANALYTIC / CLIENT) =======================

ADMIN_ROLES = {"AUTHORITY", "ANALYTIC"}


def get_user_roles(user) -> list[str]:
    """
    Пытаемся аккуратно вытащить роли из объекта user,
    ориентируясь на HKRolesTypes = 'AUTHORITY' | 'ANALYTIC' | 'CLIENT'.
    """
    if not getattr(user, "is_authenticated", False):
        return []

    roles: list[str] = []

    # Вариант 1: user.roles = ["AUTHORITY", "ANALYTIC"]
    if hasattr(user, "roles"):
        val = getattr(user, "roles")
        if isinstance(val, str):
            roles.append(val)
        elif isinstance(val, (list, tuple, set)):
            roles.extend(val)

    # Вариант 2: user.authorities = ["AUTHORITY", ...]
    if hasattr(user, "authorities"):
        val = getattr(user, "authorities")
        if isinstance(val, str):
            roles.append(val)
        elif isinstance(val, (list, tuple, set)):
            roles.extend(val)

    # Вариант 3: user.role = "CLIENT"
    if hasattr(user, "role"):
        val = getattr(user, "role")
        if isinstance(val, str):
            roles.append(val)

    return [str(r).upper() for r in roles if r]


def has_role(user, role: str) -> bool:
    return role.upper() in get_user_roles(user)


def is_analytic_user(user) -> bool:
    return has_role(user, "ANALYTIC")


def is_authority_user(user) -> bool:
    return has_role(user, "AUTHORITY")


def is_admin_user(user) -> bool:
    """
    ADMIN в нашем смысле: AUTHORITY или ANALYTIC.
    """
    return any(r in ADMIN_ROLES for r in get_user_roles(user))


def check_case_access(user, case: "Case") -> None:
    """
    - AUTHORITY / ANALYTIC: доступ ко всем кейсам
    - остальные (CLIENT): только к кейсам, где requester_id = user.id
    """
    if not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required")

    if is_admin_user(user):
        return

    if case.requester_id and case.requester_id != str(user.id):
        raise PermissionDenied("You do not have access to this case")


# ======================= Views кейсов =======================


@extend_schema(
    tags=['Cases'],
    summary='Создать кейс (сессию) / получить список кейсов',
    description=(
        'Шаг 1. Создаёт новый бизнес-кейс/сессию. '
        'На этом шаге пользователь указывает только название (title) '
        'и, опционально, своё имя. В ответ возвращается uid кейса.\n\n'
        'GET /api/cases/:\n'
        '- CLIENT видит только СВОИ кейсы (requester_id = user.id)\n'
        '- AUTHORITY и ANALYTIC видят ВСЕ кейсы.'
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
    GET  /api/cases/   — список кейсов:
         - CLIENT: только свои
         - AUTHORITY / ANALYTIC: все
    POST /api/cases/   — создать новый кейс (сессию)
    """
    queryset = Case.objects.all().order_by("-created_at")
    serializer_class = CaseSessionCreateSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not getattr(user, "is_authenticated", False):
            return qs.none()

        # админы (AUTHORITY / ANALYTIC) видят все кейсы
        if is_admin_user(user):
            return qs

        # обычный клиент — только свои
        return qs.filter(requester_id=str(user.id))


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
    summary='Получить или удалить кейс',
    description=(
        'GET — детальная информация по кейсу: название, статус, инициатор, '
        'ответы на стартовые вопросы и выбранные типы документов.\n\n'
        'DELETE — удалить кейс:\n'
        '- CLIENT может удалять только свои кейсы;\n'
        '- AUTHORITY и ANALYTIC могут удалять любые кейсы.'
    ),
    responses={200: CaseDetailSerializer},
)
class CaseDetailView(generics.GenericAPIView):
    """
    GET    /api/cases/{id}/      — посмотреть кейс
    DELETE /api/cases/{id}/      — удалить кейс
    """
    serializer_class = CaseDetailSerializer

    def get_object(self) -> Case:
        try:
            case = Case.objects.get(pk=self.kwargs["pk"])
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        check_case_access(self.request.user, case)
        return case

    def get(self, request, pk, *args, **kwargs):
        case = self.get_object()
        serializer = self.get_serializer(case)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        case = self.get_object()
        case.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

        check_case_access(request.user, case)

        all_questions = case.followup_questions.all()
        total_questions = all_questions.count()

        next_question = all_questions.filter(
            status=FollowupQuestionStatus.PENDING
        ).order_by("order_index").first()

        if next_question is None:
            # нет ни одного ожидающего вопроса
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

        check_case_access(request.user, case)

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
