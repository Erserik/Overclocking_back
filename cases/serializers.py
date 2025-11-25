from rest_framework import serializers
from .models import Case, CaseStatus, FollowupQuestion, FollowupQuestionStatus
from .services.followup import generate_followup_questions_for_case


# Ключи для 8 обязательных вопросов
REQUIRED_ANSWER_KEYS = [
    "idea",
    "target_users",
    "problem",
    "ideal_flow",
    "user_actions",
    "mvp",
    "constraints",
    "success_criteria",
]


class CaseSessionCreateSerializer(serializers.ModelSerializer):
    """
    Шаг 1: создание кейса/сессии.
    Принимает:
    - title (обязательно)
    - requester_name (опционально)
    """

    class Meta:
        model = Case
        fields = (
            "id",
            "title",
            "requester_name",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")

    def create(self, validated_data):
        request = self.context.get("request")
        requester_id = None
        if request is not None:
            requester_id = request.META.get("HTTP_X_USER_ID")

        case = Case.objects.create(
            requester_id=requester_id,
            status=CaseStatus.DRAFT,
            **validated_data,
        )
        return case


class CaseInitialAnswersSerializer(serializers.ModelSerializer):
    """
    Шаг 2: сохранение ответов на 8 вопросов и типов документов
    для уже созданного кейса.

    После успешного сохранения вызываем генерацию плана уточняющих вопросов.
    """

    class Meta:
        model = Case
        fields = (
            "id",
            "title",
            "requester_name",
            "status",
            "initial_answers",
            "selected_document_types",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "title",
            "requester_name",
            "status",
            "created_at",
            "updated_at",
        )

    def validate_initial_answers(self, value):
        if value is None:
            raise serializers.ValidationError("initial_answers is required")

        missing = [k for k in REQUIRED_ANSWER_KEYS if k not in value]
        if missing:
            raise serializers.ValidationError(
                f"Missing required keys in initial_answers: {', '.join(missing)}"
            )

        for key in REQUIRED_ANSWER_KEYS:
            v = value.get(key)
            if not isinstance(v, str) or not v.strip():
                raise serializers.ValidationError(
                    f"Field '{key}' must be a non-empty string"
                )

        return value

    def validate_selected_document_types(self, value):
        if value is None:
            return value

        if not isinstance(value, list):
            raise serializers.ValidationError("selected_document_types must be a list")

        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError(
                    "Each document type code must be a string"
                )

        return value

    def update(self, instance, validated_data):
        """
        Обновляем initial_answers и selected_document_types,
        ставим статус IN_PROGRESS и генерируем план уточняющих вопросов.
        """
        initial_answers = validated_data.get("initial_answers")
        selected_document_types = validated_data.get("selected_document_types")

        if initial_answers is not None:
            instance.initial_answers = initial_answers

        if selected_document_types is not None:
            instance.selected_document_types = selected_document_types

        instance.status = CaseStatus.IN_PROGRESS
        instance.save()

        # Генерация плана уточняющих вопросов (сейчас — заглушка)
        generate_followup_questions_for_case(instance)

        instance.refresh_from_db()
        return instance


# --------- НОВОЕ: сериализатор для уточняющих вопросов ---------


class FollowupQuestionSerializer(serializers.ModelSerializer):
    """
    Используется внутри детального кейса, чтобы показать
    все уточняющие вопросы и ответы на них.
    """

    class Meta:
        model = FollowupQuestion
        fields = (
            "id",
            "order_index",
            "code",
            "text",
            "target_document_types",
            "status",
            "answer_text",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


# --------- Детальный кейс с вложенными вопросами ---------


class CaseDetailSerializer(serializers.ModelSerializer):
    """
    Детальный просмотр кейса.
    Теперь включает список уточняющих вопросов и ответов.
    """

    followup_questions = FollowupQuestionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Case
        fields = (
            "id",
            "title",
            "status",
            "requester_name",
            "initial_answers",
            "selected_document_types",
            "created_at",
            "updated_at",
            "followup_questions",   # <- добавили
        )


# --------- Сериализаторы для next-question / answer-question ---------


class NextQuestionResponseSerializer(serializers.Serializer):
    """
    Ответ API на запрос следующего уточняющего вопроса.
    """
    question_id = serializers.UUIDField(allow_null=True)
    order_index = serializers.IntegerField(allow_null=True)
    total_questions = serializers.IntegerField()
    text = serializers.CharField(allow_null=True)
    target_document_types = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )
    is_finished = serializers.BooleanField()


class AnswerQuestionSerializer(serializers.Serializer):
    """
    Тело запроса при ответе на уточняющий вопрос.
    """
    question_id = serializers.UUIDField()
    answer = serializers.CharField(
        allow_blank=False,
        help_text="Ответ пользователя на уточняющий вопрос.",
    )
