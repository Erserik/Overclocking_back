from django.urls import path
from .views import CaseDocumentsEnsureListView

urlpatterns = [
    path("cases/<uuid:pk>/documents/", CaseDocumentsEnsureListView.as_view(), name="case-documents-ensure-list"),
]
