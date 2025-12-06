from rest_framework import serializers

from .models import GeneratedDocument, DocumentStatus, DocumentVersion


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор для документа:
    - docx_url: абсолютная ссылка на DOCX (по FileField)
    - diagram_url: уже готовый URL на PlantUML-сервер (строка из модели)
    """

    docx_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GeneratedDocument
        fields = [
            "id",
            "case",
            "doc_type",
            "title",
            "content",
            "structured_data",
            "status",
            "generation_status",
            "llm_model",
            "prompt_version",
            "prompt_hash",
            "source_snapshot_hash",
            "error_message",
            "docx_file",
            "docx_url",
            "docx_generated_at",
            "diagram_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "case",
            "generation_status",
            "llm_model",
            "prompt_version",
            "prompt_hash",
            "source_snapshot_hash",
            "error_message",
            "docx_generated_at",
            "diagram_url",
            "created_at",
            "updated_at",
        )

    def get_docx_url(self, obj) -> str | None:
        request = self.context.get("request")
        if not obj.docx_file:
            return None
        try:
            url = obj.docx_file.url
        except ValueError:
            return None

        if request:
            return request.build_absolute_uri(url)
        return url


class DocumentReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            DocumentStatus.DRAFT,
            DocumentStatus.APPROVED_BY_BA,
            DocumentStatus.REJECTED_BY_BA,
        ]
    )


class DocumentLLMEditSerializer(serializers.Serializer):
    """
    Для текстовых документов — инструкции для GPT.
    Для диаграмм — полный PlantUML-код.
    """
    instructions = serializers.CharField(
        help_text="Инструкции для AI или полный PlantUML-код для диаграмм",
        allow_blank=False,
    )


# 🔥 НОВОЕ: версии

class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = (
            "id",
            "version",
            "title",
            "created_at",
            "reason",
        )


class DocumentVersionSelectSerializer(serializers.Serializer):
    """
    Тело запроса для выбора версии.
    Можно передать либо version_id, либо номер version.
    """
    version_id = serializers.UUIDField(required=False)
    version = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        if not attrs.get("version_id") and not attrs.get("version"):
            raise serializers.ValidationError("Provide either version_id or version")
        return attrs