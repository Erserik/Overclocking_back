# cases/urls.py

from django.urls import path
from .views import (
    CaseSessionCreateView,
    CaseInitialAnswersUpdateView,
    CaseDetailView,
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
]
