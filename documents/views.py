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

from .models import GeneratedDocument, DocumentType, DocumentStatus
from .serializers import (
    GeneratedDocumentSerializer,
    DocumentReviewSerializer,
    DocumentLLMEditSerializer,
)
from .services.editing import apply_llm_edit
from .services.ensure import ensure_case_documents
from .services.docx_export import ensure_docx_for_document
from .services.confluence_publish import publish_case_to_confluence
from .services.bpmn_image_export import ensure_bpmn_url_for_document

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
            # DOCX
            docx_url = None
            docx_path = None
            if doc.docx_file and doc.docx_file.name:
                docx_path = doc.docx_file.name
                docx_url = request.build_absolute_uri(doc.docx_file.url)

            # Диаграмма: только URL на PlantUML-сервер (PNG)
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

    # ---------- GET: только чтение, без генерации ----------

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

    # ---------- POST: генерация документов + файлов ----------

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
            # DOCX только для текстовых документов
            if doc.doc_type in (DocumentType.VISION, DocumentType.SCOPE):
                ensure_docx_for_document(doc, force=False)

            # Диаграмма через PlantUML URL
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
        "`approved_by_ba`, вызывается publish_case_to_confluence(case) "
        "(сейчас заглушка, которая просто ставит кейсу статус `approved`)."
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
        if not (is_analytic_user(user) or is_admin_user(user)):
            raise PermissionDenied("Only ANALYTIC or AUTHORITY can review documents")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        doc.status = new_status
        doc.save(update_fields=["status", "updated_at"])

        case = doc.case

        # если документ одобрили, проверяем, все ли доки кейса одобрены
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
    description=(
        "Позволяет роли ANALYTIC (и AUTHORITY) загрузить свой DOCX-файл для документа."
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
    summary="Отредактировать документ через AI или заменить PlantUML-код",
    description=(
        "Позволяет внести правки в уже сгенерированный документ.\n\n"
        "- Для типов `vision` и `scope` — работает через GPT: в теле запроса "
        "передаются текстовые инструкции (на русском), например:\n"
        "`\"Сделай формулировки более формальными и добавь раздел про риски внедрения\"`.\n\n"
        "- Для типов `bpmn`, `context_diagram`, `uml_use_case_diagram` — "
        "в поле `instructions` передаётся **полный PlantUML-код диаграммы**, "
        "который полностью заменяет старый и используется для перегенерации PNG-ссылки.\n\n"
        "Править могут все пользователи, у которых есть доступ к кейсу "
        "(CLIENT — только свои кейсы, ANALYTIC/AUTHORITY/ADMIN — любые).\n\n"
        "Результат: обновлённый structured_data, контент и (при необходимости) DOCX/diagram_url."
    ),
    request=DocumentLLMEditSerializer,
    responses={200: GeneratedDocumentSerializer},
)
class DocumentLLMEditView(generics.GenericAPIView):
    """
    POST /api/documents/{id}/llm-edit/

    Для текстовых документов (vision/scope):
      - instructions = текстовые правки, применяются через GPT.

    Для диаграмм (bpmn/context_diagram/uml_use_case_diagram):
      - instructions = полный PlantUML-код, которым мы заменяем существующий,
        и пересобираем ссылку на картинку (diagram_url) через PlantUML.
    """

    serializer_class = DocumentLLMEditSerializer

    def post(self, request, pk, *args, **kwargs):
        try:
            doc = GeneratedDocument.objects.select_related("case").get(pk=pk)
        except GeneratedDocument.DoesNotExist:
            raise NotFound("Document not found")

        user = request.user

        # Проверяем, что у пользователя вообще есть доступ к кейсу
        # (CLIENT — только свои кейсы, ANALYTIC/AUTHORITY/ADMIN — любые)
        check_case_access(user, doc.case)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instructions = serializer.validated_data["instructions"]

        # ---------- ВЕТКА: текстовые документы (Vision / Scope) ----------
        if doc.doc_type in (DocumentType.VISION, DocumentType.SCOPE):
            try:
                doc = apply_llm_edit(doc, instructions)
            except Exception as e:
                raise ValidationError(str(e))

            # сразу перегенерируем DOCX, чтобы был актуален
            ensure_docx_for_document(doc, force=True)

            return Response(
                GeneratedDocumentSerializer(doc).data,
                status=status.HTTP_200_OK,
            )

        # ---------- ВЕТКА: диаграммы (BPMN / Context / UML Use Case) ----------
        if doc.doc_type in (
            DocumentType.BPMN,
            DocumentType.CONTEXT_DIAGRAM,
            DocumentType.UML_USE_CASE_DIAGRAM,
        ):
            new_plantuml = (instructions or "").strip()
            if not new_plantuml:
                raise ValidationError("instructions must contain PlantUML code for diagram documents")

            structured = doc.structured_data or {}
            structured["plantuml"] = new_plantuml
            doc.structured_data = structured
            doc.content = f"```plantuml\n{new_plantuml}\n```"
            doc.save(update_fields=["structured_data", "content", "updated_at"])

            # пересобираем ссылку на диаграмму
            ensure_bpmn_url_for_document(doc, force=True)

            return Response(
                GeneratedDocumentSerializer(doc).data,
                status=status.HTTP_200_OK,
            )

        # если что-то забыли поддержать
        raise ValidationError(f"LLM edit is not supported for doc_type={doc.doc_type}")