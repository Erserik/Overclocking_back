"""
Django settings for forte_ai_back project.
Django 5.2.8
"""

import os
from pathlib import Path

from corsheaders.defaults import default_headers, default_methods

BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------
# Core / Security
# -------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

# IMPORTANT: укажи домены, которые реально ходят на Django через nginx
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "api-talap.kcmg.kz",
    "talap.kcmg.kz",
]

# Если хочешь временно оставить "*", делай только в DEBUG
if DEBUG:
    ALLOWED_HOSTS = ["*"]

TIME_ZONE = "UTC"
USE_TZ = True
LANGUAGE_CODE = "en-us"
USE_I18N = True


# -------------------------
# Apps
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",

    "drf_spectacular",
    "drf_spectacular_sidecar",

    "cases",
    "documents",
]


# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "forte_ai_back.urls"
WSGI_APPLICATION = "forte_ai_back.wsgi.application"


# -------------------------
# DRF / Swagger
# -------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "forte_ai_back.auth.SpringJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Forte AI Business Analyst API",
    "DESCRIPTION": "Сервис для сбора требований и генерации аналитических документов с помощью AI.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {
        "name": "Overclocking",
        "email": "erserikdarun82@gmail.com",
    },
    "LICENSE": {"name": "Internal use only"},
}


# -------------------------
# Templates
# -------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# -------------------------
# Database (SQLite or Postgres)
# -------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()

if DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "forte_ai"),
            "USER": os.getenv("DB_USER", "forte_ai"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }
else:
    # SQLite (временно; для прод лучше Postgres)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                # помогает при параллельных запросах (но не решает проблему полностью)
                "timeout": int(os.getenv("SQLITE_TIMEOUT", "30")),
            },
        }
    }


# ---- SQLite lock mitigation (WAL + busy_timeout) ----
# Работает только если используешь SQLite.
# Если уже на Postgres — можно не трогать.
if DB_ENGINE != "postgres":
    try:
        from django.db.backends.signals import connection_created

        def _set_sqlite_pragmas(sender, connection, **kwargs):
            if connection.vendor != "sqlite":
                return
            cursor = connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
            cursor.execute("PRAGMA busy_timeout=30000;")  # 30s

        connection_created.connect(_set_sqlite_pragmas)
    except Exception:
        pass


# -------------------------
# Password validators
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# -------------------------
# Static / Media
# -------------------------
STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -------------------------
# CORS / CSRF (важно для браузера)
# -------------------------
# В ПРОДЕ лучше не ставить ALL_ORIGINS=True
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL", "0") == "1"

CORS_ALLOWED_ORIGINS = [
    "https://talap.kcmg.kz",
    "https://api-talap.kcmg.kz",

    # дев/локал
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.8.68:5173",
]

# если ты НЕ используешь cookie-сессии, держи False
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "0") == "1"

CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
    "content-type",
]

CORS_ALLOW_METHODS = list(default_methods)

# если используешь POST из браузера — обязательно
CSRF_TRUSTED_ORIGINS = [
    "https://talap.kcmg.kz",
    "https://api-talap.kcmg.kz",
]


# -------------------------
# App config / External services
# -------------------------
AUTH_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-insecure-jwt-secret")
AUTH_JWT_ALGORITHM = "HS256"
AUTH_JWT_ISSUER = os.environ.get("JWT_ISSUER", None)

OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL_DEFAULT", "gpt-5.1")
OPENAI_MODEL_VISION = os.getenv("OPENAI_MODEL_VISION", OPENAI_MODEL_DEFAULT)
OPENAI_MODEL_SCOPE = os.getenv("OPENAI_MODEL_SCOPE", OPENAI_MODEL_DEFAULT)
OPENAI_MODEL_BPMN = os.getenv("OPENAI_MODEL_BPMN", OPENAI_MODEL_DEFAULT)
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

PLANTUML_SERVER = os.getenv("PLANTUML_SERVER", "https://www.plantuml.com/plantuml/png")

CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL", "")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME", "")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "")

OPENAI_USECASE_WORKFLOW_ID = os.getenv("OPENAI_USECASE_WORKFLOW_ID", "")
OPENAI_AGENT_MODEL = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.1-mini")