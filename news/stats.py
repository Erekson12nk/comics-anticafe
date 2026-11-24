"""Статистика заигранности: раз в месяц топ-15 игр публикуется в новостях, счетчики обнуляются."""
from django.db import transaction
from django.utils import timezone

from games.models import BoardGame

from .models import News

MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
          "сентябрь", "октябрь", "ноябрь", "декабрь"]


@transaction.atomic
def publish_monthly_top(author=None):
    """Опубликовать топ-15 игр за месяц и обнулить счетчик. Возвращает созданную новость или None."""
    top = list(BoardGame.objects.filter(plays_month__gt=0).order_by("-plays_month", "title")[:15])
    if not top:
        return None
    # Подводим итоги прошедшего месяца: команда запускается 1-го числа
    month = (timezone.localdate().replace(day=1) - timezone.timedelta(days=1))
    lines = [f"{i}. {g.title} — {g.plays_month} парт." for i, g in enumerate(top, 1)]
    news = News.objects.create(
        title=f"Топ-15 игр за {MONTHS[month.month - 1]} {month.year}",
        text="Самые заигранные настолки месяца:\n" + "\n".join(lines),
        kind=News.Kind.STATS, author=author)
    BoardGame.objects.update(plays_month=0)
    return news
