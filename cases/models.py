import uuid
from django.db import models


class CaseStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_PROGRESS = "in_progress", "In progress"
    DOCUMENTS_GENERATED = "documents_generated", "Documents generated"


class Case(models.Model):
    """
    Бизнес-кейс (заявка), вокруг которого крутится чат и документы.
    Сначала создаётся сессия (title + requester),
    потом к ней добавляются ответы на 8 вопросов и типы документов.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Название кейса / проекта / запроса
    title = models.CharField(max_length=255)

    # ID пользователя из Java/Spring авторизации
    requester_id = models.CharField(max_length=128, blank=True, null=True)
    requester_name = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(
        max_length=64,
        choices=CaseStatus.choices,
        default=CaseStatus.DRAFT,
    )

    initial_answers = models.JSONField(blank=True, null=True)

    selected_document_types = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = "Case"
        verbose_name_plural = "Cases"

    def __str__(self):
        return f"Case {self.id} (title={self.title}, status={self.status})"