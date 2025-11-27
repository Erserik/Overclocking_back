import uuid
from django.db import models

from cases.models import Case


class DocumentType(models.TextChoices):
    VISION = "vision", "Vision / Product Vision"
    SCOPE = "scope", "Scope (Solution Boundaries)"
    # позже: BRD, USE_CASE, USER_STORIES, BPMN, ...


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED_BY_BA = "approved_by_ba", "Approved by BA"
    REJECTED_BY_BA = "rejected_by_ba", "Rejected by BA"


class GenerationStatus(models.TextChoices):
    READY = "ready", "Ready"
    GENERATING = "generating", "Generating"
    FAILED = "failed", "Failed"


class GeneratedDocument(models.Model):
    """
    1 артефакт = 1 LLM вызов = 1 structured_data JSON.
    content — производный рендер из structured_data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    doc_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
    )

    # главный источник истины
    structured_data = models.JSONField(blank=True, null=True)

    # производный текст (Markdown), строим из structured_data
    title = models.CharField(max_length=255)
    content = models.TextField()

    status = models.CharField(
        max_length=50,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT,
    )

    # чтобы управление промптами было отдельным по артефактам
    prompt_version = models.CharField(max_length=50, blank=True, null=True)
    prompt_hash = models.CharField(max_length=64, blank=True, null=True)

    # чтобы понимать, что входные данные кейса поменялись
    source_snapshot_hash = models.CharField(max_length=64, blank=True, null=True)

    generation_status = models.CharField(
        max_length=20,
        choices=GenerationStatus.choices,
        default=GenerationStatus.READY,
    )
    error_message = models.TextField(blank=True, null=True)

    llm_model = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("case", "doc_type")
        ordering = ["doc_type"]

    def __str__(self):
        return f"{self.case.title} [{self.doc_type}]"
