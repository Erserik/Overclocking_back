from rest_framework import serializers

from .models import GeneratedDocument, DocumentStatus


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    """
    Общий сериализатор документа (используется в списках и детальном просмотре).
    """

    class Meta:
        model = GeneratedDocument
        fields = (
            "id",
            "case",
            "doc_type",
            "title",
            "content",
            "status",
            "generation_status",
            "llm_model",
            "structured_data",
            "prompt_version",
            "prompt_hash",
            "source_snapshot_hash",
            "error_message",
            "docx_file",
            "docx_generated_at",
            "diagram_file",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


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
