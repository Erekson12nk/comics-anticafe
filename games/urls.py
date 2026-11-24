from django.urls import path

from . import views

app_name = "games"
urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/rent/", views.rent, name="rent"),
    path("<int:pk>/review/", views.review, name="review"),
    path("<int:pk>/favorite/", views.toggle_favorite, name="favorite"),
    path("consoles/", views.consoles, name="consoles"),
]
