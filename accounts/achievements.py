"""Выдача достижений. Чтобы добавить новое: создайте Achievement в админке и допишите условие ниже."""
from .models import Achievement


def give(user, code):
    """Выдать пользователю достижение по коду (если оно заведено в админке)."""
    ach = Achievement.objects.filter(code=code).first()
    if ach and not ach.users.filter(pk=user.pk).exists():
        ach.users.add(user)
        return ach
    return None


def check_all(user):
    """Проверить простые условия. Вызывается после бронирования, аренды и отзыва."""
    if user.bookings.exists():
        give(user, "first-booking")
    if user.rentals.exists():
        give(user, "first-rental")
    if user.reviews.count() >= 5:
        give(user, "critic")
    if user.events_joined.exists():
        give(user, "party")
