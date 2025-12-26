# accounts/serializers.py
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User

ACCESS_COOKIE = "accessToken"
REFRESH_COOKIE = "refreshToken"


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "name")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class RefreshSerializer(serializers.Serializer):
    """
    Берём refresh из HttpOnly cookie refreshToken.
    Если refresh токен уже blacklisted/expired — возвращаем 401, а не 500.
    """
    def validate(self, attrs):
        request = self.context.get("request")
        refresh_str = request.COOKIES.get(REFRESH_COOKIE) if request else None

        if not refresh_str:
            raise serializers.ValidationError("No refresh token")

        try:
            refresh = RefreshToken(refresh_str)
            access = str(refresh.access_token)

            # если у тебя включена ротация refresh, можно вернуть новый refresh:
            new_refresh = str(refresh)  # по умолчанию тот же
            return {"access": access, "refresh": new_refresh}

        except TokenError:
            # blacklisted / expired / invalid
            raise serializers.ValidationError("Refresh token is invalid or expired")


class LogoutSerializer(serializers.Serializer):
    """
    Если используешь blacklist — можно заблэклистить refresh из cookie.
    """
    def save(self, **kwargs):
        request = self.context.get("request")
        refresh_str = request.COOKIES.get(REFRESH_COOKIE) if request else None
        if not refresh_str:
            return

        try:
            token = RefreshToken(refresh_str)
            token.blacklist()
        except TokenError:
            pass