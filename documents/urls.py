from django.urls import path

from .views import (
    CaseDocumentsView,
    DocumentReviewView,
    DocumentUploadDocxView,
    DocumentLLMEditView,
    DocumentVersionsListView,
    DocumentUseVersionView,
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
    path(
        "documents/<uuid:pk>/llm-edit/",
        DocumentLLMEditView.as_view(),
        name="document-llm-edit",
    ),

    # 🔥 новое
    path(
        "documents/<uuid:pk>/versions/",
        DocumentVersionsListView.as_view(),
        name="document-versions",
    ),
    path(
        "documents/<uuid:pk>/use-version/",
        DocumentUseVersionView.as_view(),
        name="document-use-version",
    ),
]