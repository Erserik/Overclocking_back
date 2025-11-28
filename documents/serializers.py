from rest_framework import serializers

from .models import GeneratedDocument, DocumentStatus


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

            # DOCX (файл + удобный абсолютный URL + дата генерации)
            "docx_file",
            "docx_url",
            "docx_generated_at",

            # Диаграмма — только URL (мы больше не храним файл)
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
        """
        Абсолютный URL до DOCX, чтобы фронту было удобно.
        """
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
    """
    Тело запроса для ревью документа (ANALYTIC / AUTHORITY).
    """

    status = serializers.ChoiceField(
        choices=[
            DocumentStatus.DRAFT,
            DocumentStatus.APPROVED_BY_BA,
            DocumentStatus.REJECTED_BY_BA,
        ]
    )

class DocumentLLMEditSerializer(serializers.Serializer):
    """
    Запрос на правку документа через AI.

    Пример тела:
    {
      "instructions": "Сделай формулировки более формальными и добавь раздел про риски внедрения."
    }
    """
    instructions = serializers.CharField(
        help_text="Инструкции для AI, как изменить документ",
        allow_blank=False,
    )