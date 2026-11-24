from django.urls import path

from . import views

app_name = "panel"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("income/", views.income, name="income"),
    path("rentals/", views.rentals, name="rentals"),
    path("rentals/<int:pk>/", views.rental_action, name="rental_action"),
    path("plays/", views.plays, name="plays"),
    path("plays/<int:pk>/", views.play_count, name="play_count"),
    path("plays/publish/", views.publish_top, name="publish_top"),
    path("map/", views.map_edit, name="map_edit"),
]
