import os
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host]

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
    "rest_framework.authtoken",
    "hr",
]

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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

if os.getenv("DATABASE_URL"):
    database_url = urlparse(os.environ["DATABASE_URL"])
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_url.path.lstrip("/"),
        "USER": database_url.username,
        "PASSWORD": database_url.password,
        "HOST": database_url.hostname,
        "PORT": database_url.port or "5432",
        "OPTIONS": {"sslmode": "require"},
    }

if os.getenv("POSTGRES_DB"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }

AUTH_PASSWORD_VALIDATORS = [] if DEBUG else [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

AUTH_MODE = os.getenv("AUTH_MODE", "local").lower()
CENTRAL_TOKEN_VERIFY_URL = os.getenv("CENTRAL_TOKEN_VERIFY_URL", "")
CENTRAL_TOKEN_FIELD = os.getenv("CENTRAL_TOKEN_FIELD", "token")
CENTRAL_API_KEY = os.getenv("CENTRAL_API_KEY", "")
CENTRAL_SYSTEM_CODE = os.getenv("CENTRAL_SYSTEM_CODE", "smart-hr")
ENABLE_MOCK_CENTRAL = os.getenv("ENABLE_MOCK_CENTRAL", "0") == "1"
MOCK_CENTRAL_TOKEN_MAX_AGE = int(os.getenv("MOCK_CENTRAL_TOKEN_MAX_AGE", "900"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
MCP_BASE_URL = RENDER_EXTERNAL_URL or "http://127.0.0.1:8000"
MCP_PUBLIC_URL = os.getenv("MCP_PUBLIC_URL", f"{MCP_BASE_URL}/mcp")
MCP_AUTH_ISSUER_URL = os.getenv("MCP_AUTH_ISSUER_URL", MCP_BASE_URL)
MCP_REQUIRED_SCOPE = os.getenv("MCP_REQUIRED_SCOPE", "smart-hr")
MCP_DRAFT_TTL_SECONDS = int(os.getenv("MCP_DRAFT_TTL_SECONDS", "600"))
default_mcp_hosts = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*"]
public_mcp_host = urlparse(MCP_PUBLIC_URL).netloc
if public_mcp_host and public_mcp_host not in default_mcp_hosts:
    default_mcp_hosts.append(public_mcp_host)
MCP_ALLOWED_HOSTS = [value for value in os.getenv(
    "MCP_ALLOWED_HOSTS",
    ",".join(default_mcp_hosts),
).split(",") if value]
MCP_ALLOWED_ORIGINS = [value for value in os.getenv(
    "MCP_ALLOWED_ORIGINS",
    "http://127.0.0.1:*,http://localhost:*",
).split(",") if value]

authentication_classes = ["rest_framework.authentication.SessionAuthentication"]
if AUTH_MODE in {"local", "hybrid"}:
    authentication_classes.insert(0, "rest_framework.authentication.TokenAuthentication")
if AUTH_MODE in {"central", "hybrid"}:
    authentication_classes.insert(0, "hr.authentication.CentralTokenAuthentication")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": authentication_classes,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Smart HR API",
    "DESCRIPTION": "智慧人資管理平台 API，提供中控系統與前端應用串接。",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "ApprovalStatusEnum": [("pending", "待審核"), ("approved", "已核准"), ("rejected", "已退回")],
        "LateNoticeStatusEnum": [("notified", "已通知主管"), ("arrived", "已到班")],
    },
}

CORS_ALLOWED_ORIGINS = [origin for origin in os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://127.0.0.1:5500,http://localhost:5500",
).split(",") if origin]
CSRF_TRUSTED_ORIGINS = [origin for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin]
AUTH_USER_MODEL = "hr.User"
