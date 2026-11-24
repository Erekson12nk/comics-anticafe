"""
python manage.py seed_demo — заполнить базу демо-данными, чтобы сразу посмотреть сайт.

Создает администратора admin (пароль из README.md), гостей, комнаты, шаблоны и мероприятия,
настолки, консоли, новости и достижения. Повторный запуск ничего не дублирует.
Настолки — из списка заведения на Tesera; цены демонстрационные, настоящие подтянет update_prices.
"""
import datetime as dt

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Achievement
from booking.models import Event, EventTemplate, Room, Visit
from games import tesera
from games.models import BoardGame, Console, ConsoleGame
from news.models import News

ADMIN_PASSWORD = "comics-admin-2026"

ROOMS = [
    ("Большой зал", "зал", 20, 0, 30, 30, 560, 330, "#2b7de9"),
    ("Комната «Таверна»", "для НРИ", 8, 400, 620, 30, 350, 240, "#ef3e36"),
    ("Консольная", "приставки", 6, 350, 620, 300, 350, 270, "#3bb273"),
    ("Уютная", "для компании", 6, 300, 30, 390, 270, 180, "#ff6fb5"),
    ("Библиотека комиксов", "чтение", 10, 0, 330, 390, 260, 180, "#ffd23f"),
]

TEMPLATES = [("Хэллоуин", "🎃", "#f97316"), ("Вафли", "🧇", "#facc15"),
             ("D&D", "🔥", "#dc2626"), ("Вечер настолки", "🎲", "#2b7de9")]

# Настолки берутся из списка заведения на Tesera (сохраненная копия games/data/tesera_games.json).
# Демо-счетчики партий, чтобы на странице статистики был график.
POPULAR = {"Колонизаторы": 31, "Каркассон": 27, "Кодовые имена": 24, "Диксит": 22, "Бэнг!": 19, "Манчкин Делюкс": 17,
           "Немезида": 15, "Ужас Аркхэма. Третья редакция": 14, "Взрывные котята": 13, "Шакал": 12, "Пандемия": 11,
           "Дюна: Империя": 10, "Кровь на часовой башне": 9, "Остров кошек": 8, "Ведьмак: Старый мир": 7, "Длина волны": 6}

CONSOLES = [
    ("Dendy", "retro", "Легенда 90-х: восьмибитные хиты в оригинальных картриджах.",
     [("Super Mario Bros.", "платформер", "Классика, с которой начинали все."),
      ("Battle City", "аркада", "Танчики на двоих — лучший способ поспорить с другом."),
      ("Chip 'n Dale", "платформер", "Кооператив про Чипа и Дейла.")]),
    ("Sega Mega Drive", "retro", "Шестнадцатибитная консоль с яркими аркадами и драками.",
     [("Sonic the Hedgehog 2", "платформер", "Самый быстрый ёж и Тейлз в кооперативе."),
      ("Mortal Kombat 3", "файтинг", "Турниры на двоих — бессмертная классика."),
      ("Comix Zone", "битемап", "Герой внутри комикса — идеально для «Com!cs».")]),
    ("PlayStation 4", "modern", "Современная консоль для компании: гонки, спорт и кооператив.",
     [("It Takes Two", "кооператив", "Лучшая игра для двоих: каждая глава — новая механика."),
      ("FIFA 23", "спорт", "Футбол на четверых."),
      ("Overcooked! 2", "кооператив", "Хаос на кухне, проверка дружбы на прочность.")]),
    ("Xbox 360", "modern", "Консоль, на которой выросло целое поколение.",
     [("Halo 3", "шутер", "Кооперативная кампания и бои на разделенном экране."),
      ("Guitar Hero III", "ритм", "Рок-концерт с пластиковой гитарой."),
      ("Gears of War 2", "шутер", "Напряженный кооператив на двоих.")]),
]

ACHIEVEMENTS = [
    ("first-booking", "Новосел", "Забронировать комнату в первый раз", "🏠"),
    ("first-rental", "Настольщик", "Взять игру домой", "📦"),
    ("critic", "Критик", "Оставить 5 отзывов", "✍️"),
    ("party", "Душа компании", "Записаться на мероприятие", "🎉"),
]


class Command(BaseCommand):
    help = "Заполняет базу демонстрационными данными"

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(username="admin", defaults={
            "is_staff": True, "is_superuser": True, "first_name": "Администратор"})
        if created:
            admin.set_password(ADMIN_PASSWORD)
            admin.save()

        for name, kind, cap, price, x, y, w, h, color in ROOMS:
            Room.objects.get_or_create(name=name, defaults=dict(kind=kind, capacity=cap, price_hour=price,
                                                                x=x, y=y, width=w, height=h, color=color))
        templates = {}
        for name, icon, color in TEMPLATES:
            templates[name], _ = EventTemplate.objects.get_or_create(name=name, defaults={"icon": icon, "color": color})

        if not BoardGame.objects.exists():
            tesera.import_items(tesera.load_cache())
            for title, plays in POPULAR.items():
                BoardGame.objects.filter(title=title).update(plays_total=plays * 3, plays_month=plays)

        for name, gen, desc, games in CONSOLES:
            console, _ = Console.objects.get_or_create(name=name, defaults={"generation": gen, "description": desc})
            for title, genre, review in games:
                ConsoleGame.objects.get_or_create(console=console, title=title, defaults={"genre": genre, "review": review})

        for code, title, desc, icon in ACHIEVEMENTS:
            Achievement.objects.get_or_create(code=code, defaults={"title": title, "description": desc, "icon": icon})

        self._events(templates)
        self._guests()
        if not News.objects.exists():
            News.objects.create(title="Сайт антикафе запущен!", kind=News.Kind.NEWS, author=admin,
                                text="Теперь комнату можно забронировать прямо на карте, а настолку — взять домой в пару кликов.")
            News.objects.create(title="Планы на зиму", kind=News.Kind.IDEAS, author=admin,
                                text="Пополняем библиотеку комиксов и готовим новогодний турнир по «Крови на часовой башне».")
        self.stdout.write(self.style.SUCCESS(f"Готово. Вход администратора: admin / {ADMIN_PASSWORD}"))

    def _events(self, templates):
        if Event.objects.exists():
            return
        tz = timezone.get_current_timezone()
        today = timezone.localdate()

        def at(days, hour):
            return timezone.make_aware(dt.datetime.combine(today + dt.timedelta(days=days), dt.time(hour)), tz)

        hall, tavern = Room.objects.get(name="Большой зал"), Room.objects.get(name="Комната «Таверна»")
        catan = BoardGame.objects.get(title="Колонизаторы")
        Event.objects.create(title="Вафельный вечер", template=templates["Вафли"], room=hall,
                             start=at(0, 18), end=at(0, 22), seats=16, description="Вафли, чай и легкие игры.")
        Event.objects.create(title="Кампания D&D: «Затерянная шахта»", template=templates["D&D"], room=tavern,
                             start=at(1, 17), end=at(1, 22), seats=5, description="Новичкам выдадим готовых персонажей.")
        Event.objects.create(title="Вечер «Колонизаторов»", template=templates["Вечер настолки"], room=hall, game=catan,
                             start=at(2, 18), end=at(2, 22), seats=8)
        Event.objects.create(title="Хэллоуин в Com!cs", template=templates["Хэллоуин"], room=None, is_big=True,
                             start=at(6, 18), end=at(6, 23), seats=40,
                             description="Костюмы, страшные истории и «Особняки безумия» до полуночи.")

    def _guests(self):
        today = timezone.localdate()
        guests = [("anya", "Аня", "Каркассон", "Ищу компанию после 18:00"),
                  ("max", "Максим", "Немезида", "Хочу разобрать правила, кто со мной?"),
                  ("lera", "Лера", "Кодовые имена", "Нас трое, нужен четвертый")]
        for i, (login, name, game, comment) in enumerate(guests):
            user, created = User.objects.get_or_create(username=login, defaults={"first_name": name})
            if created:
                user.set_unusable_password()
                user.save()
            Visit.objects.get_or_create(user=user, date=today + dt.timedelta(days=i % 2), defaults={
                "game": BoardGame.objects.filter(title=game).first(), "comment": comment})
