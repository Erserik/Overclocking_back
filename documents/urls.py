from django.urls import path

from .views import (
    CaseDocumentsView,
    DocumentReviewView,
    DocumentUploadDocxView,
)

urlpatterns = [
    path(
        "cases/<uuid:pk>/documents/",
        CaseDocumentsView.as_view(),
        name="case-documents",
    ),
    path(
        "documents/<uuid:pk>/review/",
        DocumentReviewView.as_view(),
        name="document-review",
    ),
    path(
        "documents/<uuid:pk>/upload-docx/",
        DocumentUploadDocxView.as_view(),
        name="document-upload-docx",
    ),
]
