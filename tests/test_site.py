"""Тесты основных правил сайта. Запуск: python manage.py test"""
import datetime as dt
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from booking.models import Booking, Payment, Room
from games.models import BoardGame, Rental
from news.models import News
from news.stats import publish_monthly_top


class RulesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ivan", password="test-pass-123")
        self.game = BoardGame.objects.create(title="Каркассон", price=Decimal("1990"), genre="семейная")
        self.room = Room.objects.create(name="Зал", price_hour=300)

    def test_rent_price_is_ten_percent(self):
        self.assertEqual(self.game.rent_price, Decimal("199"))

    def test_booking_overlap_forbidden(self):
        start = timezone.now() + dt.timedelta(days=1)
        Booking.objects.create(user=self.user, room=self.room, start=start, end=start + dt.timedelta(hours=2))
        b = Booking(user=self.user, room=self.room, start=start + dt.timedelta(hours=1), end=start + dt.timedelta(hours=3))
        with self.assertRaises(ValidationError):
            b.full_clean()

    def test_first_rental_only_pickup(self):
        self.client.login(username="ivan", password="test-pass-123")
        today = timezone.localdate()
        self.client.post(reverse("games:rent", args=[self.game.pk]), {
            "method": "delivery", "contact_name": "Иван", "phone": "123", "address": "ул. Ленина, 1",
            "date_from": today, "date_to": today + dt.timedelta(days=1)})
        self.assertFalse(Rental.objects.exists())
        self.client.post(reverse("games:rent", args=[self.game.pk]), {
            "method": "pickup", "contact_name": "Иван", "phone": "123",
            "date_from": today, "date_to": today + dt.timedelta(days=1)})
        rental = Rental.objects.get()
        self.assertEqual(rental.amount, Decimal("398"))

    def test_map_more_than_two_weeks_shows_oops(self):
        far = timezone.localdate() + dt.timedelta(days=20)
        resp = self.client.get(reverse("booking:map") + f"?d={far}")
        self.assertContains(resp, "нестабильное время")

    def test_demo_payment_adds_passes(self):
        self.client.login(username="ivan", password="test-pass-123")
        self.client.post(reverse("booking:buy_passes"), {"quantity": 3})
        payment = Payment.objects.get()
        self.client.post(reverse("booking:pay", args=[payment.pk]))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.passes, 3)

    def test_monthly_top_publishes_and_resets(self):
        BoardGame.objects.filter(pk=self.game.pk).update(plays_month=7, plays_total=7)
        news = publish_monthly_top()
        self.assertIn("Каркассон", news.text)
        self.assertEqual(News.objects.count(), 1)
        self.game.refresh_from_db()
        self.assertEqual(self.game.plays_month, 0)
        self.assertEqual(self.game.plays_total, 7)

    def test_pages_open(self):
        for name in ["booking:map", "booking:events", "games:catalog", "games:consoles", "news:list", "accounts:login"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(reverse("games:detail", args=[self.game.pk])).status_code, 200)

    def test_panel_only_for_staff(self):
        self.client.login(username="ivan", password="test-pass-123")
        self.assertEqual(self.client.get(reverse("panel:income")).status_code, 302)
        self.user.is_staff = True
        self.user.save()
        for name in ["panel:dashboard", "panel:income", "panel:rentals", "panel:plays", "panel:map_edit"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_tesera_import_keeps_price_and_genre(self):
        from games import tesera
        item = {"tesera_id": 707, "title": "Каркассон", "description": "Строим город", "players_min": 2,
                "players_max": 5, "play_time": 40, "age_min": 8, "year": 2000, "image_url": "",
                "genre": "семейная", "is_expansion": False}
        extra = dict(item, tesera_id=54533, title="Каркассон. Королевский Подарок", description="")
        tesera.mark_expansions([item, extra])
        self.assertTrue(extra["is_expansion"])
        self.assertEqual(tesera.import_items([item, extra]), (1, 1))
        self.game.refresh_from_db()
        self.assertEqual((self.game.tesera_id, self.game.price, self.game.players_max), (707, Decimal("1990"), 5))
        self.assertEqual(tesera.guess_genre("Древний ужас", "", 8, 14), "хоррор")
