# integrations/confluence/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .service import list_spaces_short


@extend_schema(
    tags=["Confluence"],
    summary="Список доступных Confluence spaces",
    description=(
        "Возвращает список space'ов в Confluence, чтобы пользователь мог выбрать, "
        "куда будут выгружаться артефакты / где уже лежит документация."
    ),
    responses={
        200: OpenApiResponse(
            description="Список space'ов",
            response=OpenApiTypes.OBJECT,
        )
    },
)
class ConfluenceSpacesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        spaces = list_spaces_short()
        # Можно дополнительно отсортировать по name
        spaces = sorted(spaces, key=lambda x: x["name"].lower())
        return Response({"spaces": spaces})
