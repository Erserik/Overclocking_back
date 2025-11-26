from django.urls import path

from .views import (
    GenerateDocumentsForCaseView,
    CaseDocumentsListView,
    GeneratedDocumentDetailView,
)

urlpatterns = [
    path(
        "cases/<uuid:pk>/generate-documents/",
        GenerateDocumentsForCaseView.as_view(),
        name="case-generate-documents",
    ),
    path(
        "cases/<uuid:pk>/documents/",
        CaseDocumentsListView.as_view(),
        name="case-documents-list",
    ),
    path(
        "documents/<uuid:pk>/",
        GeneratedDocumentDetailView.as_view(),
        name="document-detail",
    ),
]
