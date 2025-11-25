# cases/serializers.py

from rest_framework import serializers
from .models import Case, CaseStatus


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

    initial_answers и selected_document_types здесь не заполняем.
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
            # Можно вытаскивать ID из заголовка X-User-Id,
            # который проставит Java/Spring auth.
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

    Используется в PUT /api/cases/{id}/initial-answers/
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
        Обновляем initial_answers и selected_document_types.
        Статус можно переключить на IN_PROGRESS.
        """
        initial_answers = validated_data.get("initial_answers")
        selected_document_types = validated_data.get("selected_document_types")

        if initial_answers is not None:
            instance.initial_answers = initial_answers

        if selected_document_types is not None:
            instance.selected_document_types = selected_document_types

        # как только появились ответы, считаем, что кейс в работе
        if instance.initial_answers:
            instance.status = CaseStatus.IN_PROGRESS

        instance.save()
        return instance


class CaseDetailSerializer(serializers.ModelSerializer):
    """
    Детальный просмотр кейса.
    Пока без документов и таблиц — только данные по кейсу.
    """

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
        )
        read_only_fields = fields
