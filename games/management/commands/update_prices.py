"""python manage.py update_prices — обновить цены всех настолок с Hobby Games (запускать раз в сутки)."""
import time

from django.core.management.base import BaseCommand

from games.models import BoardGame
from games.parser import update_game


class Command(BaseCommand):
    help = "Обновляет цены настольных игр с сайта Hobby Games"

    def handle(self, *args, **options):
        ok = fail = 0
        for game in BoardGame.objects.filter(price_manual=False):
            try:
                price = update_game(game)
            except Exception as e:  # сеть, верстка — одна ошибка не должна останавливать остальные игры
                self.stderr.write(f"{game}: {e}")
                price = None
            if price:
                ok += 1
                self.stdout.write(f"{game}: {price} руб.")
            else:
                fail += 1
            time.sleep(1)  # не нагружаем чужой сайт
        self.stdout.write(self.style.SUCCESS(f"Обновлено: {ok}, не найдено: {fail}"))
