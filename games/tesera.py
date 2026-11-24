"""
Загрузка списка игр заведения с tesera.ru.

Список «Игры» пользователя Comicsnkvz: https://tesera.ru/user/2216489/lists/3630
Номер списка задан в settings.TESERA_LIST_ID. Данные берутся из открытого API Tesera:
  /collections/custom/<список>/gamesclear — какие игры в списке;
  /games/<номер игры>                     — число игроков, время партии, возраст.

Последняя загрузка сохраняется в games/data/tesera_games.json, чтобы демо-база
заполнялась и без интернета. Цены, количество экземпляров и счетчики партий
при повторной загрузке не меняются — их ведет администратор и парсер Hobby Games.
"""
import html
import json
import re
import time
from pathlib import Path

import requests

API = "https://api.tesera.ru"
HEADERS = {"User-Agent": "ComicsAnticafeBot (catalog import)"}
CACHE_FILE = Path(__file__).resolve().parent / "data" / "tesera_games.json"

# Жанр на Tesera через API не отдается, поэтому определяем его по словам в названии
# и описании. Порядок важен: первое совпадение побеждает. Жанр можно поправить в админке.
GENRE_RULES = [
    ("хоррор", r"ктулху|лавкрафт|аркхэм|ужас|особняк|зомби|вампир|дракул|кошмар|bloodborne|немезид|нечто"),
    ("детектив", r"детектив|расслед|убийств|улик|тайны аркх|шерлок"),
    ("НРИ", r"ролев|подземелья и драконы|зов ктулху: стартовый|d&d"),
    ("дуэль", r"трон куб|unmatched|битва легенд|battlecon|dice throne|bullet|для двоих|дуэл"),
    ("кооперативная", r"кооператив|вместе против|сообща|пандеми"),
    ("для вечеринок", r"вечерин|ассоциац|компани|слов|шпион|spyfall|мафи|оборот|alias|бункер|соображ|табу|экивок|кроко|уно\b|uno|свинтус|манчкин|котят|злобн"),
    ("стратегия", r"стратег|экономи|цивилизац|империя|импери|контрол|территор|дюна|dune|войн|колониз|игра престолов"),
]


def _get(url, **params):
    resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def clean_text(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def guess_genre(title, description, players_max, age_min):
    text = f"{title} {description}".lower()
    for genre, pattern in GENRE_RULES:
        if re.search(pattern, text):
            return genre
    if players_max == 2:
        return "дуэль"
    if age_min and age_min <= 8:
        return "семейная"
    return "приключения"


# Отдельные игры, которые называются как дополнения, и аксессуары, которые выглядят как игры.
STANDALONE = r"стартовый набор|делюкс|картинки|второй сезон|остров сокровищ|расширенное издание|второе издание|третья редакция$"
ACCESSORY = r"promo|промо|playmat|pack|набор|metal coins|dice set|miniature|плотва|цири"


def mark_expansions(items):
    """Дополнение — если название начинается с названия другой игры из списка
    («Колонизаторы. Мореходы»), описание начинается со слова «дополнение» или это аксессуар."""
    titles = sorted({i["title"] for i in items}, key=len)
    for item in items:
        title = item["title"].lower()
        prefix = any(item["title"] != t and re.match(re.escape(t) + r"\s*[:.\-–—]", item["title"])
                     for t in titles)
        item["is_expansion"] = not re.search(STANDALONE, title) and (re.search(ACCESSORY, title) is not None
                                or item["description"].lower().startswith("дополнени")
                                or prefix)
        if item["is_expansion"]:
            item["genre"] = "дополнение"


def fetch_list(list_id, pause=0.3, log=print):
    """Скачать все игры списка вместе с подробностями. Возвращает список словарей."""
    games, page = [], 0
    while True:
        chunk = _get(f"{API}/collections/custom/{list_id}/gamesclear", limit=100, offset=page)
        if not chunk:
            break
        games += [row["game"] for row in chunk]
        page += 1
    items = []
    for n, g in enumerate(games, 1):
        try:
            full = _get(f"{API}/games/{g['teseraId']}")["game"]
        except Exception as e:  # одна недоступная карточка не должна ломать всю загрузку
            log(f"{g['title']}: {e}")
            full = g
        description = clean_text(full.get("descriptionShort") or g.get("descriptionShort"))
        pmin = full.get("playersMin") or 2
        pmax = full.get("playersMax") or max(pmin, 4)
        age = full.get("playersAgeMin") or None
        items.append({
            "tesera_id": g["teseraId"],
            "title": g["title"].strip(),
            "description": description,
            "players_min": pmin,
            "players_max": pmax,
            "play_time": full.get("playtimeMax") or full.get("playtimeMin") or 60,
            "age_min": age,
            "year": full.get("year") or None,
            "image_url": full.get("photoUrl") or g.get("photoUrl") or "",
            "genre": guess_genre(g["title"], description, pmax, age),
        })
        if n % 50 == 0:
            log(f"загружено {n} из {len(games)}")
        time.sleep(pause)  # не нагружаем чужой сайт
    mark_expansions(items)
    return items


def save_cache(items):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def load_cache():
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def demo_price(item):
    """Ориентировочная цена до первого запуска update_prices: зависит от длительности партии."""
    return 990 + min(item["play_time"], 240) // 30 * 500 + item["tesera_id"] % 5 * 100


def import_items(items):
    """Создать новые игры и обновить описания существующих. Возвращает (создано, обновлено)."""
    from .models import BoardGame

    created = updated = 0
    for item in items:
        fields = {k: item[k] for k in ("title", "description", "players_min", "players_max", "play_time",
                                       "age_min", "year", "image_url", "is_expansion")}
        game = (BoardGame.objects.filter(tesera_id=item["tesera_id"]).first()
                or BoardGame.objects.filter(title=item["title"], tesera_id__isnull=True).first())
        if game is None:
            BoardGame.objects.create(tesera_id=item["tesera_id"], genre=item["genre"],
                                     price=demo_price(item), **fields)
            created += 1
        else:
            for k, v in fields.items():
                setattr(game, k, v)
            game.tesera_id = item["tesera_id"]
            if not game.genre:
                game.genre = item["genre"]
            game.save()
            updated += 1
    return created, updated
