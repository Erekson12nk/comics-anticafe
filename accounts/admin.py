from django.contrib import admin

from .models import Achievement, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "passes")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone")
    filter_horizontal = ("favorites",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("icon", "title", "code", "description")
    filter_horizontal = ("users",)
