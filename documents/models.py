import uuid
from django.db import models

from cases.models import Case


class DocumentType(models.TextChoices):
    VISION = "vision", "Vision / Product Vision"
    USE_CASE = "use_case", "Use Case"
    # позже можно добавить: BRD, user_story и т.п.


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED_BY_BA = "approved_by_ba", "Approved by BA"
    REJECTED_BY_BA = "rejected_by_ba", "Rejected by BA"


class GeneratedDocument(models.Model):
    """
    Документ, сгенерированный GPT на основе кейса и ответов пользователя.
    Например: Vision, Use Case и т.п.
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
        help_text="Тип документа (vision, use_case и т.д.).",
    )

    title = models.CharField(
        max_length=255,
        help_text="Заголовок документа (может быть сгенерирован из кейса).",
    )

    content = models.TextField(
        help_text="Текст документа (Markdown или обычный текст).",
    )

    status = models.CharField(
        max_length=50,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT,
        help_text="Статус документа (draft/approved/rejected).",
    )

    llm_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Название модели, которая сгенерировала документ (например, gpt-4.1-mini).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("case", "doc_type")  # один документ каждого типа на кейс
        ordering = ["doc_type"]

    def __str__(self):
        return f"{self.case.title} [{self.doc_type}]"
