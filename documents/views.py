from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from cases.models import Case
from cases.views import check_case_access  # ✅ используем общую логику доступа
from documents.models import GeneratedDocument
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

    def _build_files_payload(self, request, case: Case):
        """
        Вспомогательный метод: собрать payload по всем документам кейса.
        НЕ вызывает ensure_case_documents, ожидает, что docs уже существуют.
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

        # Проверка прав: CLIENT только свои кейсы, AUTHORITY/ANALYTIC — все
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
            "Шаги внутри:\n"
            "1) ensure_case_documents(case) — создаёт отсутствующие документы (vision, scope и т.п.);\n"
            "   если документ уже есть и structured_data не пустой — GPT повторно НЕ вызывается;\n"
            "2) ensure_docx_for_document(doc) — для каждого документа создаёт DOCX, если его ещё нет;\n"
            "3) Возвращает JSON со списком файлов: id, doc_type, title, docx_url, docx_path.\n\n"
            "Права доступа такие же, как у GET:\n"
            "- CLIENT может генерировать документы только по своим кейсам;\n"
            "- AUTHORITY и ANALYTIC — по любому кейсу."
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

        # 3) собираем актуальный список файлов
        files = self._build_files_payload(request, case)

        payload = {
            "case_id": str(case.id),
            "case_title": case.title,
            "did_generate_any": did_generate_any,
            "errors": errors,
            "files": files,
        }
        return Response(payload, status=status.HTTP_200_OK)
