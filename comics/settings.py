"""
Настройки сайта антикафе «Com!cs».

Секретные значения (ключи VK, ЮKassa, пароль БД) берутся из переменных окружения,
чтобы не хранить их в коде. Для локальной разработки ничего задавать не нужно.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me-on-server")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
# на хостинге с HTTPS: адреса сайта для проверки форм, например https://имя.pythonanywhere.com
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "social_django",
    "accounts",
    "games",
    "booking",
    "news",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "comics.urls"

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
                "social_django.context_processors.backends",
                "accounts.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "comics.wsgi.application"

# База данных: по умолчанию SQLite (файл db.sqlite3), на сервере — PostgreSQL,
# если задана переменная POSTGRES_DB.
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# Вход: через VK ID (social-auth) или логин/пароль (для администраторов)
AUTHENTICATION_BACKENDS = [
    "social_core.backends.vk.VKOAuth2",
    "django.contrib.auth.backends.ModelBackend",
]
SOCIAL_AUTH_VK_OAUTH2_KEY = os.environ.get("VK_APP_ID", "")
SOCIAL_AUTH_VK_OAUTH2_SECRET = os.environ.get("VK_APP_SECRET", "")
SOCIAL_AUTH_VK_OAUTH2_SCOPE = ["email"]
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "accounts.pipeline.save_vk_avatar",
)
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "booking:map"
LOGOUT_REDIRECT_URL = "booking:map"

# Онлайн-оплата ЮKassa. Пока ключи не заданы, работает демо-оплата.
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Asia/Novokuznetsk"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Правила заведения, которые удобно менять в одном месте
RENT_PERCENT_PER_DAY = 10      # аренда настолки за сутки, процентов от цены игры
BOOKING_DAYS_AHEAD = 14        # на сколько дней вперед можно смотреть карту и бронировать
PASS_PRICE = 300               # стоимость одной «проходки», руб.
TESERA_LIST_ID = 3630          # список игр заведения на tesera.ru (команда import_tesera)
