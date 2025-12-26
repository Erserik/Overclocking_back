# accounts/authentication.py
from __future__ import annotations

from typing import Optional, Tuple

from rest_framework.authentication import BaseAuthentication


class CookieJWTAuthentication(BaseAuthentication):
    """
    Берём access JWT из cookie 'accessToken'.
    Если cookie нет — fallback на обычный Authorization: Bearer.
    """

    access_cookie_name = "accessToken"

    def _jwt(self):
        # ВАЖНО: импорт внутри, чтобы не ломать загрузку Django/Swagger при ошибках
        from rest_framework_simplejwt.authentication import JWTAuthentication

        return JWTAuthentication()

    def authenticate(self, request) -> Optional[Tuple[object, object]]:
        jwt_auth = self._jwt()

        raw = request.COOKIES.get(self.access_cookie_name)
        if raw:
            validated = jwt_auth.get_validated_token(raw)
            user = jwt_auth.get_user(validated)
            return (user, validated)

        # fallback: Authorization: Bearer <token>
        return jwt_auth.authenticate(request)