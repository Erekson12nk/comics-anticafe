from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Room(models.Model):
    """Комната на карте заведения. x, y, width, height — положение прямоугольника на SVG-карте (0–1000 × 0–600)."""
    name = models.CharField("название", max_length=60)
    kind = models.CharField("тип", max_length=60, blank=True, help_text="Например: зал, VIP-комната, консольная")
    capacity = models.PositiveSmallIntegerField("вместимость", default=6)
    price_hour = models.DecimalField("цена часа, руб.", max_digits=8, decimal_places=2, default=0)
    x = models.PositiveIntegerField(default=20)
    y = models.PositiveIntegerField(default=20)
    width = models.PositiveIntegerField(default=200)
    height = models.PositiveIntegerField(default=150)
    color = models.CharField("цвет", max_length=7, default="#3b82f6")

    class Meta:
        verbose_name = "комната"
        verbose_name_plural = "комнаты"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Booking(models.Model):
    class Purpose(models.TextChoices):
        PARTY = "party", "Праздник"
        RPG = "rpg", "НРИ (D&D)"
        CHILL = "chill", "Просто посидеть"

    class Status(models.TextChoices):
        WAITING = "waiting", "Ожидает оплаты"
        PAID = "paid", "Оплачено"
        CANCELED = "canceled", "Отменено"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings", verbose_name="комната")
    start = models.DateTimeField("начало")
    end = models.DateTimeField("окончание")
    purpose = models.CharField("цель", max_length=10, choices=Purpose.choices, default=Purpose.CHILL)
    comment = models.CharField("комментарий", max_length=200, blank=True)
    amount = models.DecimalField("сумма, руб.", max_digits=9, decimal_places=2, default=0)
    status = models.CharField("статус", max_length=10, choices=Status.choices, default=Status.WAITING)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "бронирование"
        verbose_name_plural = "бронирования"
        ordering = ["start"]

    def __str__(self):
        return f"{self.room} {self.start:%d.%m %H:%M}"

    def clean(self):
        if self.end <= self.start:
            raise ValidationError("Время окончания должно быть позже начала.")
        overlap = Booking.objects.filter(room=self.room, start__lt=self.end, end__gt=self.start) \
            .exclude(status=Booking.Status.CANCELED).exclude(pk=self.pk)
        if overlap.exists():
            raise ValidationError("Комната уже занята в это время.")

    def hours(self):
        return (self.end - self.start).total_seconds() / 3600


class Visit(models.Model):
    """Планируемое посещение: по нему над картой показываются аватарки гостей."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visits")
    date = models.DateField("дата")
    game = models.ForeignKey("games.BoardGame", on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name="хочу поиграть в")
    comment = models.CharField("комментарий", max_length=150, blank=True)

    class Meta:
        verbose_name = "планируемое посещение"
        verbose_name_plural = "планируемые посещения"
        unique_together = ("user", "date")
        ordering = ["date"]


class EventTemplate(models.Model):
    """Шаблон мероприятия: картинка, которая всплывает на комнате карты."""
    name = models.CharField("название", max_length=80)
    icon = models.CharField("значок (эмодзи)", max_length=8, default="🎲",
                            help_text="Например 🎃 для Хэллоуина, 🧇 для вафель, 🔥 для D&D")
    image = models.ImageField("картинка", upload_to="templates/", blank=True)
    description = models.TextField("описание по умолчанию", blank=True)
    color = models.CharField("цвет", max_length=7, default="#f59e0b")

    class Meta:
        verbose_name = "шаблон мероприятия"
        verbose_name_plural = "шаблоны мероприятий"

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField("название", max_length=120)
    template = models.ForeignKey(EventTemplate, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="шаблон")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="комната")
    game = models.ForeignKey("games.BoardGame", on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name="настолка вечера",
                             help_text="Если выбрана, на комнате показывается картинка игры")
    start = models.DateTimeField("начало")
    end = models.DateTimeField("окончание")
    description = models.TextField("описание", blank=True)
    seats = models.PositiveSmallIntegerField("мест", default=10)
    is_big = models.BooleanField("масштабное событие", default=False)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="events_joined")

    class Meta:
        verbose_name = "мероприятие"
        verbose_name_plural = "мероприятия"
        ordering = ["start"]

    def __str__(self):
        return self.title

    def free_seats(self):
        return max(self.seats - self.participants.count(), 0)

    def icon(self):
        return self.template.icon if self.template else "⭐"

    def picture(self):
        if self.game and self.game.image_src():
            return self.game.image_src()
        if self.template and self.template.image:
            return self.template.image.url
        return ""


class Payment(models.Model):
    class Kind(models.TextChoices):
        PASSES = "passes", "Проходки"
        BOOKING = "booking", "Бронирование"
        RENTAL = "rental", "Аренда игры"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SUCCEEDED = "succeeded", "Оплачен"
        CANCELED = "canceled", "Отменен"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    kind = models.CharField("назначение", max_length=10, choices=Kind.choices)
    amount = models.DecimalField("сумма, руб.", max_digits=9, decimal_places=2)
    quantity = models.PositiveSmallIntegerField("количество проходок", default=0)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    rental = models.ForeignKey("games.Rental", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField("статус", max_length=10, choices=Status.choices, default=Status.PENDING)
    external_id = models.CharField("номер платежа в ЮKassa", max_length=64, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "платеж"
        verbose_name_plural = "платежи"
        ordering = ["-created"]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount} руб."
