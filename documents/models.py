import uuid
from django.db import models

from cases.models import Case


class DocumentType(models.TextChoices):
    VISION = "vision", "Vision / Product Vision"
    SCOPE = "scope", "Scope"
    # дальше можно добавить: BRD, use_case, и т.п.


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED_BY_BA = "approved_by_ba", "Approved by BA"
    REJECTED_BY_BA = "rejected_by_ba", "Rejected by BA"


class GenerationStatus(models.TextChoices):
    NEW = "new", "New"
    GENERATING = "generating", "Generating"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class GeneratedDocument(models.Model):
    """
    Документ, сгенерированный GPT на основе кейса и ответов пользователя.
    Например: Vision, Scope и т.п.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="Кейс, для которого сгенерирован документ.",
    )

    doc_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        help_text="Тип документа (vision, scope, use_case и т.д.).",
    )

    title = models.CharField(
        max_length=255,
        help_text="Заголовок документа (может быть сгенерирован из кейса).",
    )

    # Markdown/текстовая версия
    content = models.TextField(
        blank=True,
        help_text="Текст документа (Markdown или обычный текст).",
    )

    # Структурный JSON (P.0: Vision/Scope)
    structured_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Структурированное представление документа (JSON), для доработок и экспорта.",
    )

    status = models.CharField(
        max_length=50,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT,
        help_text="Статус документа (draft/approved/rejected).",
    )

    generation_status = models.CharField(
        max_length=50,
        choices=GenerationStatus.choices,
        default=GenerationStatus.NEW,
        help_text="Статус генерации (new/generating/ready/failed).",
    )

    llm_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Название модели, которая сгенерировала документ (например, gpt-4.1-mini).",
    )

    prompt_version = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Версия промпта для этого типа документа.",
    )

    prompt_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Хеш system+user промпта для определения устаревания.",
    )

    source_snapshot_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Хеш исходных данных кейса (initial_answers + followups), на базе которых генерился документ.",
    )

    # ✅ DOCX-экспорт
    docx_file = models.FileField(
        upload_to="generated_docs/",
        blank=True,
        null=True,
        help_text="Сгенерированный DOCX файл (экспорт).",
    )

    docx_generated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Когда был сгенерирован DOCX.",
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Сообщение об ошибке при генерации, если была.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("case", "doc_type")  # один документ каждого типа на кейс
        ordering = ["doc_type"]

    def __str__(self):
        return f"{self.case.title} [{self.doc_type}]"
