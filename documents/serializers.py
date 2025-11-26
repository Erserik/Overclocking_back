from rest_framework import serializers

from .models import GeneratedDocument


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    """
    Используется для отображения документа (список и детальный просмотр).
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
            "llm_model",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
