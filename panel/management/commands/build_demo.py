"""
python manage.py build_demo — собрать статичную демо-версию сайта (для GitHub Pages).

Страницы рендерятся как для гостя и сохраняются в обычные HTML-файлы. Вход, бронь, аренда
и оплата в демо-версии отключены (переменная DEMO в шаблонах). Ссылки с параметрами
(?d=дата, ?page=2, ?kind=...) превращаются в отдельные страницы, потому что статичный
хостинг параметры не обрабатывает.

  --out    папка для сборки (по умолчанию demo_build)
  --base   адрес сайта от корня домена, для GitHub Pages это /имя-репозитория/
"""
import datetime as dt
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client
from django.utils import timezone

from booking.models import Event
from games.models import BoardGame
from news.models import News

PAGE_SIZE = 24  # как в games.views.catalog


class Command(BaseCommand):
    help = "Собирает статичную демо-версию сайта"

    def add_arguments(self, parser):
        parser.add_argument("--out", default="demo_build")
        parser.add_argument("--base", default="/comics-anticafe/")

    def handle(self, *args, out, base, **options):
        settings.STATIC_DEMO = True
        if "testserver" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append("testserver")
        self.out, self.base = Path(out), "/" + base.strip("/") + "/" if base.strip("/") else "/"
        shutil.rmtree(self.out, ignore_errors=True)
        self.client = Client()

        today = timezone.localdate()
        pages = {"/": "", "/events/": "events/", "/games/": "games/", "/games/consoles/": "games/consoles/",
                 "/news/": "news/"}
        for i in range(settings.BOOKING_DAYS_AHEAD + 2):
            day = today + dt.timedelta(days=i)
            pages[f"/?d={day}"] = f"day/{day}/"
        self.last_day = str(day)  # последний день уже показывает «ошибочку», дальше листать некуда
        n_games = BoardGame.objects.filter(is_expansion=False).count()
        for n in range(2, (n_games - 1) // PAGE_SIZE + 2):
            pages[f"/games/?page={n}"] = f"games/page/{n}/"
        for pk in BoardGame.objects.values_list("pk", flat=True):
            pages[f"/games/{pk}/"] = f"games/{pk}/"
        for kind, _ in News.Kind.choices:
            pages[f"/news/?kind={kind}"] = f"news/kind/{kind}/"

        for url, path in pages.items():
            resp = self.client.get(url)
            if resp.status_code != 200:
                self.stderr.write(f"{url}: {resp.status_code}")
                continue
            html = self.rewrite(resp.content.decode("utf-8"), url)
            target = self.out / path / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html, encoding="utf-8")

        shutil.copytree(settings.BASE_DIR / "static", self.out / "static")
        (self.out / ".nojekyll").write_text("")  # GitHub Pages не трогает папки, начинающиеся с «_»
        shutil.copy(self.out / "index.html", self.out / "404.html")
        self.stdout.write(self.style.SUCCESS(f"Готово: {len(pages)} страниц в {self.out}"))

    def rewrite(self, html, url):
        b = self.base
        here = url.split("?")[0]

        def query_link(m):
            query = m.group(2)
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            path = m.group(1) or here
            if path == "/" and params.get("d"):
                return f'href="{b}day/{min(params["d"], self.last_day)}/"'
            if path == "/games/" and params.get("page"):
                return f'href="{b}games/"' if params["page"] == "1" else f'href="{b}games/page/{params["page"]}/"'
            if path == "/news/":
                return f'href="{b}news/kind/{params["kind"]}/"' if params.get("kind") else f'href="{b}news/"'
            return f'href="{b}{path.lstrip("/")}"'

        # ссылки с параметрами: ?d=..., ?page=..., ?kind=..., /account/login/?next=...
        html = re.sub(r'href="(/[^"?]*)?\?([^"]*)"', query_link, html)
        # остальные ссылки от корня сайта получают адрес репозитория
        if b != "/":
            html = re.sub(r'(href|src|action)="/(?!/)', rf'\1="{b}', html)
            html = html.replace(f'{b}{b.lstrip("/")}', b)
        return html
