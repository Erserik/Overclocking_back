from rest_framework import serializers
from .models import GeneratedDocument


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedDocument
        fields = (
            "id",
            "case",
            "doc_type",
            "title",
            "structured_data",
            "content",
            "status",
            "generation_status",
            "error_message",
            "prompt_version",
            "prompt_hash",
            "source_snapshot_hash",
            "llm_model",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EnsureDocumentsResponseSerializer(serializers.Serializer):
    documents = GeneratedDocumentSerializer(many=True)
    errors = serializers.DictField(child=serializers.CharField())
    did_generate_any = serializers.BooleanField()
