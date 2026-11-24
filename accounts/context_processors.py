from django.conf import settings


def site(request):
    """Переменные, доступные во всех шаблонах."""
    return {
        "VK_LOGIN_ENABLED": bool(settings.SOCIAL_AUTH_VK_OAUTH2_KEY),
        "PASS_PRICE": settings.PASS_PRICE,
        "DEMO": getattr(settings, "STATIC_DEMO", False),
    }
