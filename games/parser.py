"""
Загрузка цен настольных игр с сайта Hobby Games.

Если у игры заполнено поле «страница игры в Hobby Games», цена берется с этой страницы.
Иначе выполняется поиск по названию и берется первый результат.
Игры с отметкой «цена задана вручную» не трогаются.

Если Hobby Games поменяет верстку, поправьте селекторы PRICE_SELECTORS / CARD_SELECTOR ниже.
"""
import re
from decimal import Decimal
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

BASE = "https://hobbygames.ru"
SEARCH_URL = BASE + "/catalog/search?keyword={}"
HEADERS = {"User-Agent": "Mozilla/5.0 (ComicsAnticafeBot; price update once a day)"}
PRICE_SELECTORS = [".product-price-card__price", ".product-card-price", "[itemprop=price]"]
CARD_SELECTOR = "a.product-card__image, .product-card a"


def parse_price(text):
    """'1 990 ₽' -> Decimal('1990')"""
    digits = re.sub(r"[^\d]", "", text or "")
    return Decimal(digits) if digits else None


def _get(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def price_from_page(url):
    soup = _get(url)
    for sel in PRICE_SELECTORS:
        tag = soup.select_one(sel)
        if tag:
            price = parse_price(tag.get("content") or tag.get_text())
            if price:
                return price
    return None


def find_game_url(title):
    soup = _get(SEARCH_URL.format(quote(title)))
    link = soup.select_one(CARD_SELECTOR)
    return urljoin(BASE, link["href"]) if link and link.get("href") else None


def update_game(game):
    """Обновить цену одной игры. Возвращает новую цену или None, если найти не удалось."""
    if game.price_manual:
        return None
    url = game.price_url or find_game_url(game.title)
    if not url:
        return None
    price = price_from_page(url)
    if price:
        game.price = price
        game.price_url = url
        game.price_updated = timezone.now()
        game.save(update_fields=["price", "price_url", "price_updated"])
    return price
