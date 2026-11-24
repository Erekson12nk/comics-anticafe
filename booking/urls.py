from django.urls import path

from . import views

app_name = "booking"
urlpatterns = [
    path("", views.map_view, name="map"),
    path("room/<int:room_id>/book/", views.book_room, name="book_room"),
    path("visit/", views.plan_visit, name="plan_visit"),
    path("events/", views.events_view, name="events"),
    path("events/<int:event_id>/toggle/", views.toggle_event, name="toggle_event"),
    path("passes/buy/", views.buy_passes, name="buy_passes"),
    path("pay/<int:payment_id>/", views.pay, name="pay"),
    path("pay/yookassa/webhook/", views.yookassa_webhook, name="yookassa_webhook"),
]
