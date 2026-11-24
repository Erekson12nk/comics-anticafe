from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("booking.urls")),
    path("account/", include("accounts.urls")),
    path("games/", include("games.urls")),
    path("news/", include("news.urls")),
    path("panel/", include("panel.urls")),
    path("social/", include("social_django.urls", namespace="social")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Com!cs — администрирование"
admin.site.site_title = "Com!cs"
