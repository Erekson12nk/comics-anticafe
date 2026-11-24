from django.contrib import admin

from .models import MoneyEntry


@admin.register(MoneyEntry)
class MoneyEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "kind", "amount", "note")
    list_filter = ("kind",)
