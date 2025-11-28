# cases/models.py
import uuid
from django.db import models


class CaseStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_PROGRESS = "in_progress", "In progress"
    READY_FOR_DOCUMENTS = "ready_for_documents", "Ready for documents"
    DOCUMENTS_GENERATED = "documents_generated", "Documents generated"
    APPROVED = "approved", "Approved"  # ✅ когда все документы приняты


class Case(models.Model):
    """
    Бизнес-кейс (заявка), вокруг которого крутится чат и документы.
    Флоу:
    1) Создаём кейс (title + requester).
    2) Заполняем 8 базовых ответов + выбираем типы документов.
    3) Генерируем план уточняющих вопросов.
    4) Пользователь отвечает на уточняющие вопросы.
    5) Генерируем документы.
    6) Аналитик/заказчик утверждает документы -> статус APPROVED.
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

    # Ответы на 8 стартовых вопросов
    initial_answers = models.JSONField(blank=True, null=True)

    # Выбранные типы документов (например ["scope", "use_case"])
    selected_document_types = models.JSONField(blank=True, null=True)

    # ✅ выбранное Confluence-пространство (для привязки артефактов)
    confluence_space_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Ключ выбранного пространства Confluence (например, PROD-BANK)",
    )
    confluence_space_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Человекочитаемое имя пространства Confluence",
    )

    class Meta:
        verbose_name = "Case"
        verbose_name_plural = "Cases"

    def __str__(self):
        return f"Case {self.id} (title={self.title}, status={self.status})"


class FollowupQuestionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ANSWERED = "answered", "Answered"
    SKIPPED = "skipped", "Skipped"


class FollowupQuestion(models.Model):
    """
    Уточняющий вопрос, который нужно задать по кейсу (план вопросов).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    case = models.ForeignKey(
        Case,
        related_name="followup_questions",
        on_delete=models.CASCADE,
    )

    # Порядок задавания вопросов (0, 1, 2, ...)
    order_index = models.PositiveIntegerField(default=0)

    # Машинное имя (опционально): "roles", "channels", "non_functional" и т.п.
    code = models.CharField(max_length=128, blank=True, null=True)

    # Текст вопроса, который увидит пользователь
    text = models.TextField()

    # На какие типы документов этот вопрос больше всего влияет
    # Например: ["scope", "use_case"]
    target_document_types = models.JSONField(blank=True, null=True)

    status = models.CharField(
        max_length=32,
        choices=FollowupQuestionStatus.choices,
        default=FollowupQuestionStatus.PENDING,
    )

    # Ответ пользователя на этот вопрос (сохраняем как текст)
    answer_text = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Follow-up question"
        verbose_name_plural = "Follow-up questions"
        ordering = ["order_index", "created_at"]

    def __str__(self):
        return f"FollowupQuestion {self.id} for case {self.case_id} ({self.status})"
