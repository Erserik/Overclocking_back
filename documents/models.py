import uuid
from django.db import models

from cases.models import Case


class DocumentType(models.TextChoices):
    VISION = "vision", "Vision / Product Vision"
    SCOPE = "scope", "Scope / Product Scope"
    BPMN = "bpmn", "BPMN Diagram"
    # позже: BRD, user_stories, context_diagram и т.п.


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
    Документ или диаграмма, сгенерированные GPT на основе кейса и ответов пользователя.
    Например: Vision, Scope, BPMN и т.п.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="Кейс, для которого сгенерирован документ/диаграмма.",
    )

    doc_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        help_text="Тип документа (vision, scope, bpmn и т.д.).",
    )

    title = models.CharField(max_length=255)

    # Markdown / текстовое представление (для Vision/Scope, для BPMN – описание + ```plantuml``` блок)
    content = models.TextField(blank=True)

    # Структурированный JSON (для Vision/Scope – разделы, для BPMN – plantuml + метаданные)
    structured_data = models.JSONField(blank=True, null=True)

    status = models.CharField(
        max_length=50,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT,
    )

    generation_status = models.CharField(
        max_length=50,
        choices=GenerationStatus.choices,
        default=GenerationStatus.NEW,
    )

    llm_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Имя модели, которая генерировала документ.",
    )

    prompt_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Версия промпта для этого документа.",
    )

    prompt_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Хэш system+user промпта для определения устаревания.",
    )

    source_snapshot_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Хэш кейса/ответов, на основе которых был сгенерен документ.",
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Текст ошибки генерации, если что-то пошло не так.",
    )

    # DOCX для текстовых документов (Vision, Scope и т.п.)
    docx_file = models.FileField(
        upload_to="generated_docs/",
        blank=True,
        null=True,
        help_text="DOCX-версия документа (для текстовых документов).",
    )

    docx_generated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Когда последний раз генерировался DOCX.",
    )

    # ✅ только ссылка на картинку диаграммы на PlantUML-сервере
    diagram_url = models.URLField(
        blank=True,
        null=True,
        help_text="External PlantUML server image URL for diagram-like documents.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Generated document"
        verbose_name_plural = "Generated documents"
        ordering = ["case", "doc_type", "created_at"]

    def __str__(self):
        return f"{self.doc_type} for case={self.case_id} ({self.id})"
