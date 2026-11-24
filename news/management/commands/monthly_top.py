"""python manage.py monthly_top — опубликовать топ-15 игр месяца и обнулить счетчики (запускать 1-го числа)."""
from django.core.management.base import BaseCommand

from news.stats import publish_monthly_top


class Command(BaseCommand):
    help = "Публикует топ-15 игр по заигранности и обнуляет месячный счетчик"

    def handle(self, *args, **options):
        news = publish_monthly_top()
        self.stdout.write(self.style.SUCCESS(f"Опубликовано: {news}") if news else "За месяц нет партий")
