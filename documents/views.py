from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from drf_spectacular.utils import extend_schema

from cases.models import Case
from .serializers import EnsureDocumentsResponseSerializer
from .services.ensure import ensure_case_documents


@extend_schema(
    tags=["Documents"],
    summary="Получить документы по кейсу (lazy generation P.0)",
    description=(
        "Возвращает список документов по кейсу. "
        "Если vision/scope отсутствуют, создаёт их на лету (1 документ = 1 LLM вызов)."
    ),
    responses={200: EnsureDocumentsResponseSerializer},
)
class CaseDocumentsEnsureListView(generics.GenericAPIView):
    serializer_class = EnsureDocumentsResponseSerializer

    def get(self, request, pk, *args, **kwargs):
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            raise NotFound("Case not found")

        user = request.user
        if getattr(user, "is_authenticated", False):
            if case.requester_id and case.requester_id != str(user.id):
                raise PermissionDenied("You do not have access to this case")

        try:
            docs, errors, did_generate_any = ensure_case_documents(case)
        except ValueError as e:
            raise ValidationError(str(e))

        resp = {
            "documents": docs,
            "errors": errors,
            "did_generate_any": did_generate_any,
        }
        return Response(self.get_serializer(resp).data, status=status.HTTP_200_OK)
