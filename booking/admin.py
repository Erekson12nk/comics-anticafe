from django.contrib import admin

from .models import Booking, Event, EventTemplate, Payment, Room, Visit


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "capacity", "price_hour")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("room", "user", "start", "end", "purpose", "amount", "status")
    list_filter = ("status", "room", "purpose")
    date_hierarchy = "start"


@admin.register(EventTemplate)
class EventTemplateAdmin(admin.ModelAdmin):
    list_display = ("icon", "name")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "template", "room", "start", "seats", "is_big")
    list_filter = ("template", "is_big")
    filter_horizontal = ("participants",)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "game", "comment")
    date_hierarchy = "date"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("created", "user", "kind", "amount", "status", "external_id")
    list_filter = ("kind", "status")
