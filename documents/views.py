from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from drf_spectacular.utils import extend_schema, OpenApiExample

from cases.models import Case
from .models import GeneratedDocument
from .serializers import GeneratedDocumentSerializer
from .services import generate_documents_for_case


@extend_schema(
    tags=['Documents'],
    summary='Сгенерировать документы по кейсу',
    description=(
        'Шаг 4. На основе кейса, стартовых ответов и уточняющих ответов '
        'генерирует аналитические документы (например, Vision, Use Case) '
        'с помощью GPT и сохраняет их в базе. Возвращает список документов.'
    ),
    responses={200: GeneratedDocumentSerializer(many=True)},
    examples=[
        OpenApiExample(
            'Пример ответа',
            value=[
                {
                    "id": "11111111-2222-3333-4444-555555555555",
                    "case": "3d6241d5-6aec-4e96-a6b2-8ac4e79f0ea5",
                    "doc_type": "vision",
                    "title": "Vision документа для AI-ассистента",
                    "content": "# Vision\n\n...",
                    "status": "draft",
                    "llm_model": "gpt-4.1-mini",
                    "created_at": "2025-11-26T09:00:00Z",
                    "updated_at": "2025-11-26T09:00:00Z"
                }
            ],
            response_only=True,
        ),
    ],
)
class GenerateDocumentsForCaseView(generics.GenericAPIView):
    """
    POST /api/cases/{id}/generate-documents/
    """
    serializer_class = GeneratedDocumentSerializer

    def post(self, request, pk, *args, **kwargs):
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        docs = generate_documents_for_case(case)
        serializer = self.get_serializer(docs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Documents'],
    summary='Список документов по кейсу',
    description='Возвращает список всех документов, сгенерированных для указанного кейса.',
    responses={200: GeneratedDocumentSerializer(many=True)},
)
class CaseDocumentsListView(generics.ListAPIView):
    """
    GET /api/cases/{id}/documents/
    """
    serializer_class = GeneratedDocumentSerializer

    def get_queryset(self):
        case_id = self.kwargs["pk"]
        return GeneratedDocument.objects.filter(case_id=case_id).order_by("doc_type")


@extend_schema(
    tags=['Documents'],
    summary='Детальный просмотр документа',
    description='Возвращает один сгенерированный документ по его id.',
    responses={200: GeneratedDocumentSerializer},
)
class GeneratedDocumentDetailView(generics.RetrieveAPIView):
    """
    GET /api/documents/{id}/
    """
    queryset = GeneratedDocument.objects.all()
    serializer_class = GeneratedDocumentSerializer
    lookup_field = "pk"
