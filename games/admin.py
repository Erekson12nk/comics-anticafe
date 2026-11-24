from django.contrib import admin

from .models import BoardGame, Console, ConsoleGame, Rental, Review


@admin.register(BoardGame)
class BoardGameAdmin(admin.ModelAdmin):
    list_display = ("title", "genre", "price", "rent_price", "price_manual", "copies", "plays_month")
    list_editable = ("price", "price_manual", "copies")
    list_filter = ("genre", "is_expansion", "price_manual")
    search_fields = ("title",)

    @admin.display(description="аренда в сутки")
    def rent_price(self, obj):
        return obj.rent_price


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ("game", "user", "method", "date_from", "date_to", "returned_at", "paid", "status")
    list_filter = ("status", "method", "paid")
    search_fields = ("game__title", "user__username", "contact_name", "phone")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("game", "user", "rating", "created")


class ConsoleGameInline(admin.TabularInline):
    model = ConsoleGame
    extra = 1


@admin.register(Console)
class ConsoleAdmin(admin.ModelAdmin):
    list_display = ("name", "generation")
    list_filter = ("generation",)
    inlines = [ConsoleGameInline]


@admin.register(ConsoleGame)
class ConsoleGameAdmin(admin.ModelAdmin):
    list_display = ("title", "console", "genre")
    list_filter = ("console",)
    search_fields = ("title",)
