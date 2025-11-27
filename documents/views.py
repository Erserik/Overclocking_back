from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser

from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from django.utils import timezone

from cases.models import Case, CaseStatus
from cases.views import check_case_access, is_admin_user, is_analytic_user
from .models import GeneratedDocument
from .serializers import GeneratedDocumentSerializer, DocumentReviewSerializer
from .services.ensure import ensure_case_documents
from .services.docx_export import ensure_docx_for_document


@extend_schema(
    tags=["Documents"],
    summary="Список документов по кейсу (без генерации)",
    description=(
        "GET: возвращает список уже сгенерированных документов по кейсу и ссылки на DOCX, "
        "НЕ создавая новые документы.\n\n"
        "Права доступа:\n"
        "- CLIENT видит документы только своих кейсов;\n"
        "- AUTHORITY и ANALYTIC могут видеть документы любого кейса."
    ),
    responses={
        200: OpenApiResponse(
            description="Список документов и DOCX-файлов по кейсу",
            response=OpenApiTypes.OBJECT,
        )
    },
)
class CaseDocumentsView(generics.GenericAPIView):
    """
    GET  /api/cases/{id}/documents/  — просто достаёт текущие документы (без генерации)
    POST /api/cases/{id}/documents/  — генерирует/обновляет документы и DOCX
    """

    serializer_class = GeneratedDocumentSerializer  # чтобы DRF не ругался

    def _build_files_payload(self, request, case: Case):
        """
        Собрать payload по всем документам кейса.
        """
        docs = list(
            GeneratedDocument.objects.filter(case=case).order_by("doc_type")
        )

        files = []
        for doc in docs:
            docx_url = None
            docx_path = None
            if doc.docx_file and doc.docx_file.name:
                docx_path = doc.docx_file.name
                docx_url = request.build_absolute_uri(doc.docx_file.url)

            files.append(
                {
                    "id": str(doc.id),
                    "doc_type": doc.doc_type,
                    "title": doc.title,
                    "status": doc.status,
                    "generation_status": doc.generation_status,
                    "docx_url": docx_url,
                    "docx_path": docx_path,
                }
            )

        return files

    # ---------- GET: только чтение ----------

    def get(self, request, pk, *args, **kwargs):
        """
        Возвращает только то, что уже есть.
        Никаких новых вызовов GPT и генерации DOCX.
        """
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        check_case_access(request.user, case)

        files = self._build_files_payload(request, case)

        payload = {
            "case_id": str(case.id),
            "case_title": case.title,
            "did_generate_any": False,
            "errors": {},
            "files": files,
        }
        return Response(payload, status=status.HTTP_200_OK)

    # ---------- POST: генерация документов + DOCX ----------

    @extend_schema(
        tags=["Documents"],
        summary="Сгенерировать/обновить документы по кейсу и вернуть список DOCX-файлов",
        description=(
            "POST: запускает генерацию документов по кейсу (vision/scope и др.) и создание DOCX.\n\n"
            "Права доступа такие же, как у GET:\n"
            "- CLIENT может генерировать документы только по своим кейсам;\n"
            "- AUTHORITY и ANALYTIC — по любому кейсу.\n\n"
            "Если хотя бы один документ был сгенерирован впервые, "
            "статус кейса переводится в `documents_generated`."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Список документов и DOCX-файлов по кейсу после генерации",
                response=OpenApiTypes.OBJECT,
            )
        },
    )
    def post(self, request, pk, *args, **kwargs):
        """
        Генерирует документы (если их ещё нет) и DOCX-файлы, затем возвращает список.
        Если что-то сгенерировали впервые — помечаем кейс как DOCUMENTS_GENERATED.
        """
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        check_case_access(request.user, case)

        # 1) лениво генерим JSON/Markdown-документы
        try:
            docs, errors, did_generate_any = ensure_case_documents(case)
        except Exception as e:
            raise ValidationError(str(e))

        # 2) для каждого документа убеждаемся, что есть DOCX (если уже есть — не пересоздаём)
        for doc in docs:
            ensure_docx_for_document(doc, force=False)

        # 3) если реально что-то сгенерили впервые — обновляем статус кейса
        if did_generate_any and case.status != CaseStatus.DOCUMENTS_GENERATED:
            case.status = CaseStatus.DOCUMENTS_GENERATED
            case.save(update_fields=["status"])

        # 4) собираем актуальный список файлов
        files = self._build_files_payload(request, case)

        payload = {
            "case_id": str(case.id),
            "case_title": case.title,
            "did_generate_any": did_generate_any,
            "errors": errors,
            "files": files,
        }
        return Response(payload, status=status.HTTP_200_OK)


# ======================= Ревью документа ANALYTIC =======================


@extend_schema(
    tags=["Documents"],
    summary="Подтвердить или отклонить документ (роль ANALYTIC / AUTHORITY)",
    description=(
        "Позволяет роли ANALYTIC (и AUTHORITY) менять статус документа: "
        "draft / approved_by_ba / rejected_by_ba.\n\n"
        "CLIENT не имеет доступа к этому методу."
    ),
    request=DocumentReviewSerializer,
    responses={200: GeneratedDocumentSerializer},
)
class DocumentReviewView(generics.GenericAPIView):
    """
    PATCH /api/documents/{id}/review/
    """
    serializer_class = DocumentReviewSerializer

    def patch(self, request, pk, *args, **kwargs):
        try:
            doc = GeneratedDocument.objects.select_related("case").get(pk=pk)
        except GeneratedDocument.DoesNotExist:
            raise NotFound("Document not found")

        user = request.user
        # только ANALYTIC / AUTHORITY
        if not (is_analytic_user(user) or is_admin_user(user)):
            raise PermissionDenied("Only ANALYTIC or AUTHORITY can review documents")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        doc.status = new_status
        doc.save(update_fields=["status", "updated_at"])

        return Response(
            GeneratedDocumentSerializer(doc).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Documents"],
    summary="Заменить DOCX-файл документа (роль ANALYTIC / AUTHORITY)",
    description=(
        "Позволяет роли ANALYTIC (и AUTHORITY) загрузить свой DOCX-файл для документа.\n"
        "Файл полностью заменяет сгенерированный. CLIENT не имеет доступа."
    ),
    request=None,
    responses={
        200: OpenApiResponse(
            description="Обновлённый документ с новой ссылкой на DOCX",
            response=GeneratedDocumentSerializer,
        )
    },
)
class DocumentUploadDocxView(generics.GenericAPIView):
    """
    POST /api/documents/{id}/upload-docx/
    """
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = GeneratedDocumentSerializer  # только для схемы

    def post(self, request, pk, *args, **kwargs):
        try:
            doc = GeneratedDocument.objects.select_related("case").get(pk=pk)
        except GeneratedDocument.DoesNotExist:
            raise NotFound("Document not found")

        user = request.user
        if not (is_analytic_user(user) or is_admin_user(user)):
            raise PermissionDenied("Only ANALYTIC or AUTHORITY can upload DOCX")

        file_obj = request.FILES.get("file")
        if not file_obj:
            raise ValidationError("No file uploaded. Use form-data field 'file'.")

        # Заменяем файл
        doc.docx_file = file_obj
        doc.docx_generated_at = timezone.now()
        doc.save(update_fields=["docx_file", "docx_generated_at", "updated_at"])

        return Response(
            GeneratedDocumentSerializer(doc).data,
            status=status.HTTP_200_OK,
        )
