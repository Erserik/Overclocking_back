from django.urls import path

from .views import CaseDocumentsView

urlpatterns = [
    path(
        "cases/<uuid:pk>/documents/",
        CaseDocumentsView.as_view(),
        name="case-documents",
    ),
]
