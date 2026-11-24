"""python manage.py import_tesera — загрузить каталог настолок из списка заведения на tesera.ru.

  --offline  взять сохраненную копию games/data/tesera_games.json (без интернета)
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from games import tesera


class Command(BaseCommand):
    help = "Загружает список игр заведения с tesera.ru в каталог настольных игр"

    def add_arguments(self, parser):
        parser.add_argument("--offline", action="store_true", help="использовать сохраненную копию списка")

    def handle(self, *args, offline=False, **options):
        if offline:
            items = tesera.load_cache()
        else:
            items = tesera.fetch_list(settings.TESERA_LIST_ID, log=self.stdout.write)
            tesera.save_cache(items)
        created, updated = tesera.import_items(items)
        self.stdout.write(self.style.SUCCESS(f"Игр в списке: {len(items)}, добавлено: {created}, обновлено: {updated}"))
