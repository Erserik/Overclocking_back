import logging
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser

from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from cases.models import Case, CaseStatus
from cases.views import check_case_access, is_admin_user, is_analytic_user

from .models import (
    GeneratedDocument,
    DocumentType,
    DocumentStatus,
    DocumentVersion,
)
from .serializers import (
    GeneratedDocumentSerializer,
    DocumentReviewSerializer,
    DocumentLLMEditSerializer,
    DocumentVersionSerializer,
    DocumentVersionSelectSerializer,
)
from .services.editing import apply_llm_edit
from .services.ensure import ensure_case_documents
from .services.docx_export import ensure_docx_for_document
from .services.confluence_publish import publish_case_to_confluence
from .services.bpmn_image_export import ensure_bpmn_url_for_document
from .services.versioning import create_document_version_snapshot
from .services.diagram_editing import apply_diagram_llm_edit  # important

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Documents"],
    summary="Список документов по кейсу (без генерации)",
    description=(
        "GET: возвращает список уже сгенерированных документов по кейсу и ссылки на файлы, "
        "НЕ создавая новые документы и НЕ вызывая LLM.\n\n"
        "Права доступа:\n"
        "- CLIENT видит документы только своих кейсов;\n"
        "- AUTHORITY и ANALYTIC могут видеть документы любого кейса."
    ),
    responses={
        200: OpenApiResponse(
            description="Список документов и связанных файлов по кейсу",
            response=OpenApiTypes.OBJECT,
        )
    },
)
class CaseDocumentsView(generics.GenericAPIView):
    """
    GET  /api/cases/{id}/documents/  — просто достаёт текущие документы (без генерации LLM)
    POST /api/cases/{id}/documents/  — генерирует/обновляет документы и файлы (DOCX + diagram_url)
    """

    serializer_class = GeneratedDocumentSerializer

    def _build_files_payload(self, request, case: Case):
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

            diagram_url = doc.diagram_url
            diagram_path = None  # локальных файлов не храним

            files.append(
                {
                    "id": str(doc.id),
                    "doc_type": doc.doc_type,
                    "title": doc.title,
                    "status": doc.status,
                    "generation_status": doc.generation_status,
                    "docx_url": docx_url,
                    "docx_path": docx_path,
                    "diagram_url": diagram_url,
                    "diagram_path": diagram_path,
                }
            )

        return files

    def get(self, request, pk, *args, **kwargs):
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

    @extend_schema(
        tags=["Documents"],
        summary="Сгенерировать/обновить документы по кейсу и вернуть список файлов",
        description=(
            "POST: запускает ленивую генерацию документов по кейсу (vision/scope/bpmn/context/use case) "
            "и создание файлов:\n"
            "- для текстовых документов — DOCX;\n"
            "- для диаграмм (BPMN, context_diagram, uml_use_case_diagram) — только URL на PlantUML-сервер.\n"
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Список документов и файлов по кейсу после генерации",
                response=OpenApiTypes.OBJECT,
            )
        },
    )
    def post(self, request, pk, *args, **kwargs):
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        check_case_access(request.user, case)

        try:
            docs, errors, did_generate_any = ensure_case_documents(case)
        except Exception as e:
            raise ValidationError(str(e))

        for doc in docs:
            if doc.doc_type in (DocumentType.VISION, DocumentType.SCOPE):
                ensure_docx_for_document(doc, force=False)

            if doc.doc_type in (
                DocumentType.BPMN,
                DocumentType.CONTEXT_DIAGRAM,
                DocumentType.UML_USE_CASE_DIAGRAM,
            ):
                ensure_bpmn_url_for_document(doc, force=False)

        if did_generate_any and case.status != CaseStatus.DOCUMENTS_GENERATED:
            case.status = CaseStatus.DOCUMENTS_GENERATED
            case.save(update_fields=["status"])

        files = self._build_files_payload(request, case)

        payload = {
            "case_id": str(case.id),
            "case_title": case.title,
            "did_generate_any": did_generate_any,
            "errors": errors,
            "files": files,
        }
        return Response(payload, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Documents"],
    summary="Подтвердить или отклонить документ (роль ANALYTIC / AUTHORITY)",
    description=(
        "Позволяет роли ANALYTIC (и AUTHORITY) менять статус документа: "
        "`draft` / `approved_by_ba` / `rejected_by_ba`.\n\n"
        "Если после изменения статуса ВСЕ документы кейса имеют статус "
        "`approved_by_ba`, вызывается publish_case_to_confluence(case)."
    ),
    request=DocumentReviewSerializer,
    responses={200: GeneratedDocumentSerializer},
)
class DocumentReviewView(generics.GenericAPIView):
    serializer_class = DocumentReviewSerializer

    def patch(self, request, pk, *args, **kwargs):
        try:
            doc = GeneratedDocument.objects.select_related("case").get(pk=pk)
        except GeneratedDocument.DoesNotExist:
            raise NotFound("Document not found")

        user = request.user
        if not (is_analytic_user(user) or is_admin_user(user)):
            raise PermissionDenied("Only ANALYTIC or AUTHORITY can review documents")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        doc.status = new_status
        doc.save(update_fields=["status", "updated_at"])

        case = doc.case

        if new_status == DocumentStatus.APPROVED_BY_BA:
            all_docs = list(case.documents.all())
            if all_docs and all(
                d.status == DocumentStatus.APPROVED_BY_BA for d in all_docs
            ):
                try:
                    publish_case_to_confluence(case)
                except Exception as e:
                    logger.exception(
                        "Failed to publish case %s to Confluence: %s",
                        case.id,
                        e,
                    )

        return Response(
            GeneratedDocumentSerializer(doc).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Documents"],
    summary="Заменить DOCX-файл документа (роль ANALYTIC / AUTHORITY)",
    description="Позволяет роли ANALYTIC (и AUTHORITY) загрузить свой DOCX-файл для документа.",
    request=None,
    responses={
        200: OpenApiResponse(
            description="Обновлённый документ с новой ссылкой на DOCX",
            response=GeneratedDocumentSerializer,
        )
    },
)
class DocumentUploadDocxView(generics.GenericAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = GeneratedDocumentSerializer

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

        doc.docx_file = file_obj
        doc.docx_generated_at = timezone.now()
        doc.save(update_fields=["docx_file", "docx_generated_at", "updated_at"])

        return Response(
            GeneratedDocumentSerializer(doc).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Documents"],
    summary="Отредактировать документ через AI (текст) или диаграмму (через AI + PlantUML)",
    description=(
        "Для типов `vision` и `scope` — работает через GPT (instructions = текстовые правки).\n"
        "Для типов `bpmn`, `context_diagram`, `uml_use_case_diagram` — "
        "instructions = текстовые инструкции на русском, GPT возвращает новый PlantUML.\n"
        "После правок создаётся новая версия документа."
    ),
    request=DocumentLLMEditSerializer,
    responses={200: GeneratedDocumentSerializer},
)
class DocumentLLMEditView(generics.GenericAPIView):
    serializer_class = DocumentLLMEditSerializer

    def post(self, request, pk, *args, **kwargs):
        try:
            doc = GeneratedDocument.objects.select_related("case").get(pk=pk)
        except GeneratedDocument.DoesNotExist:
            raise NotFound("Document not found")

        user = request.user
        check_case_access(user, doc.case)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instructions = serializer.validated_data["instructions"]

        # Text documents
        if doc.doc_type in (DocumentType.VISION, DocumentType.SCOPE):
            try:
                doc = apply_llm_edit(doc, instructions)
            except Exception as e:
                raise ValidationError(str(e))

            ensure_docx_for_document(doc, force=True)
            create_document_version_snapshot(doc, reason="llm_edit")

            return Response(
                GeneratedDocumentSerializer(doc).data,
                status=status.HTTP_200_OK,
            )

        # Diagrams via AI + context
        if doc.doc_type in (
            DocumentType.BPMN,
            DocumentType.CONTEXT_DIAGRAM,
            DocumentType.UML_USE_CASE_DIAGRAM,
        ):
            try:
                doc = apply_diagram_llm_edit(doc, instructions)
            except Exception as e:
                raise ValidationError(str(e))

            ensure_bpmn_url_for_document(doc, force=True)
            create_document_version_snapshot(doc, reason="diagram_edit")

            return Response(
                GeneratedDocumentSerializer(doc).data,
                status=status.HTTP_200_OK,
            )

        raise ValidationError(f"LLM edit is not supported for doc_type={doc.doc_type}")


@extend_schema(
    tags=["Documents"],
    summary="Список версий документа",
    description="Возвращает историю версий документа, по убыванию номера версии.",
    responses={200: DocumentVersionSerializer(many=True)},
)
class DocumentVersionsListView(generics.GenericAPIView):
    serializer_class = DocumentVersionSerializer

    def get(self, request, pk, *args, **kwargs):
        try:
            doc = GeneratedDocument.objects.select_related("case").get(pk=pk)
        except GeneratedDocument.DoesNotExist:
            raise NotFound("Document not found")

        check_case_access(request.user, doc.case)

        versions = doc.versions.all().order_by("-version")
        serializer = self.get_serializer(versions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Documents"],
    summary="Сделать выбранную версию текущей",
    description=(
        "Копирует title/content/structured_data из указанной версии в текущий документ, "
        "перегенерирует DOCX/diagram_url и создаёт новую версию с reason='restore_version'."
    ),
    request=DocumentVersionSelectSerializer,
    responses={200: GeneratedDocumentSerializer},
)
class DocumentUseVersionView(generics.GenericAPIView):
    serializer_class = DocumentVersionSelectSerializer

    def post(self, request, pk, *args, **kwargs):
        try:
            doc = GeneratedDocument.objects.select_related("case").get(pk=pk)
        except GeneratedDocument.DoesNotExist:
            raise NotFound("Document not found")

        check_case_access(request.user, doc.case)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        version_obj = None
        if data.get("version_id"):
            try:
                version_obj = DocumentVersion.objects.get(
                    document=doc,
                    id=data["version_id"],
                )
            except DocumentVersion.DoesNotExist:
                raise NotFound("Version not found for this document")
        else:
            try:
                version_obj = DocumentVersion.objects.get(
                    document=doc,
                    version=data["version"],
                )
            except DocumentVersionDoesNotExist:
                raise NotFound("Version not found for this document")

        # подмена текущего состояния документа
        doc.title = version_obj.title
        doc.content = version_obj.content
        doc.structured_data = version_obj.structured_data
        doc.save(update_fields=["title", "content", "structured_data", "updated_at"])

        # перегенерим файлы/диаграммы
        if doc.doc_type in (DocumentType.VISION, DocumentType.SCOPE):
            ensure_docx_for_document(doc, force=True)

        if doc.doc_type in (
            DocumentType.BPMN,
            DocumentType.CONTEXT_DIAGRAM,
            DocumentType.UML_USE_CASE_DIAGRAM,
        ):
            ensure_bpmn_url_for_document(doc, force=True)

        # создаём ещё одну версию как результат отката
        create_document_version_snapshot(doc, reason="restore_version")

        return Response(
            GeneratedDocumentSerializer(doc).data,
            status=status.HTTP_200_OK,
        )

