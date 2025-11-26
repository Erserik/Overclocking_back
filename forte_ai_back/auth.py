import jwt
from dataclasses import dataclass
from typing import Optional, Tuple, Any

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions


@dataclass
class SpringUser:
    """
    Простая обёртка над данными из JWT.
    Не привязана к django.contrib.auth.User, чтобы не городить лишнюю БД.
    """
    id: str
    role: Optional[str] = None
    name: Optional[str] = None

    @property
    def is_authenticated(self) -> bool:
        return True

    def __str__(self) -> str:
        return self.name or self.id


class SpringJWTAuthentication(BaseAuthentication):
    """
    Аутентификация через JWT, выданный Spring Auth-сервисом.

    Ожидает заголовок:
        Authorization: Bearer <jwt>

    Проверяет подпись с помощью JWT_SECRET (общий с Spring),
    опционально проверяет issuer,
    и достаёт из payload поля: sub, role, name.
    """

    keyword = "Bearer"

    def authenticate(self, request) -> Optional[Tuple[SpringUser, Any]]:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header:
            # Нет заголовка Authorization — DRF потом решит,
            # что делать в зависимости от permission_classes.
            return None

        parts = auth_header.split()

        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed(
                "Invalid Authorization header format. Expected: 'Bearer <token>'."
            )

        token = parts[1]

        decode_kwargs = {
            "key": settings.AUTH_JWT_SECRET,
            "algorithms": [settings.AUTH_JWT_ALGORITHM],
            "options": {"verify_aud": False},
        }
        if settings.AUTH_JWT_ISSUER:
            decode_kwargs["issuer"] = settings.AUTH_JWT_ISSUER

        try:
            payload = jwt.decode(**decode_kwargs, jwt=token)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired.")
        except jwt.InvalidIssuerError:
            raise exceptions.AuthenticationFailed("Invalid token issuer.")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token.")

        # Предполагаем, что Spring кладёт в токен:
        # sub  -> идентификатор пользователя
        # role -> роль (INITIATOR / BA_ADMIN / ...)
        # name -> имя (опционально)
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise exceptions.AuthenticationFailed("Token payload has no 'sub' claim.")

        role = payload.get("role")
        name = payload.get("name")

        user = SpringUser(id=str(user_id), role=role, name=name)

        # Второй элемент кортежа — дополнительная инфа об аутентификации (payload)
        return user, payload
