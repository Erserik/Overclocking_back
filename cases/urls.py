from django.urls import path
from .views import (
    CaseSessionCreateView,
    CaseInitialAnswersUpdateView,
    CaseDetailView,
    NextFollowupQuestionView,
    AnswerFollowupQuestionView,
)

urlpatterns = [
    # Шаг 1 — создать кейс/сессию
    path("cases/", CaseSessionCreateView.as_view(), name="case-create"),

    # Детальный просмотр кейса
    path("cases/<uuid:pk>/", CaseDetailView.as_view(), name="case-detail"),

    # Шаг 2 — записать 8 вопросов + типы документов
    path(
        "cases/<uuid:pk>/initial-answers/",
        CaseInitialAnswersUpdateView.as_view(),
        name="case-initial-answers",
    ),

    # Шаг 3 — получить следующий уточняющий вопрос
    path(
        "cases/<uuid:pk>/next-question/",
        NextFollowupQuestionView.as_view(),
        name="case-next-question",
    ),

    # Шаг 3 — ответить на уточняющий вопрос
    path(
        "cases/<uuid:pk>/answer-question/",
        AnswerFollowupQuestionView.as_view(),
        name="case-answer-question",
    ),
]
