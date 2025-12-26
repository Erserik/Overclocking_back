# accounts/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import RegisterSerializer, LoginSerializer, LogoutSerializer

ACCESS_COOKIE = "access"
REFRESH_COOKIE = "refresh"


def _cookie_flags():
    return dict(
        httponly=True,
        secure=False,
        samesite="Lax",
        path="/",
    )


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        user = s.validated_data["user"]
        access = s.validated_data["access"]
        refresh = s.validated_data["refresh"]

        resp = Response(
            {
                "access": access,
                "refresh": refresh,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": getattr(user, "name", "") or "",
                    "role": getattr(user, "role", None),
                },
            },
            status=status.HTTP_200_OK,
        )

        resp.set_cookie(ACCESS_COOKIE, access, **_cookie_flags())
        resp.set_cookie(REFRESH_COOKIE, refresh, **_cookie_flags())
        return resp


class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]


    def post(self, request, *args, **kwargs):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        refresh_str = request.COOKIES.get(REFRESH_COOKIE) or request.data.get("refresh")
        if not refresh_str:
            return Response({"detail": "No refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            old_refresh = RefreshToken(refresh_str)

            new_access = str(old_refresh.access_token)

            user_id = old_refresh.get("user_id")
            if not user_id:
                raise TokenError("Refresh token has no user_id")

            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)

            new_refresh_obj = RefreshToken.for_user(user)
            new_refresh = str(new_refresh_obj)

            try:
                old_refresh.blacklist()
            except Exception:
                pass

        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_401_UNAUTHORIZED)
        except TokenError:
            return Response({"detail": "Refresh token invalid"}, status=status.HTTP_401_UNAUTHORIZED)

        resp = Response(
            {
                "access": new_access,
                "refresh": new_refresh,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": getattr(user, "name", "") or "",
                    "role": getattr(user, "role", None),
                },
            },
            status=status.HTTP_200_OK,
        )
        resp.set_cookie(ACCESS_COOKIE, new_access, **_cookie_flags())
        resp.set_cookie(REFRESH_COOKIE, new_refresh, **_cookie_flags())
        return resp

class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()  # blacklist refresh (если включён blacklist)

        resp = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)
        resp.delete_cookie(ACCESS_COOKIE, path="/")
        resp.delete_cookie(REFRESH_COOKIE, path="/")
        return resp


class MeView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        u = request.user
        return Response(
            {
                "id": str(u.id),
                "email": u.email,
                "name": getattr(u, "name", "") or "",
                "role": getattr(u, "role", None),
            },
            status=status.HTTP_200_OK,
        )