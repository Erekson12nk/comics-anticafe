from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse


class BoardGame(models.Model):
    """Настольная игра из каталога."""
    title = models.CharField("название", max_length=150)
    description = models.TextField("краткое описание", blank=True)
    genre = models.CharField("жанр", max_length=60, blank=True)
    players_min = models.PositiveSmallIntegerField("игроков от", default=2)
    players_max = models.PositiveSmallIntegerField("игроков до", default=4)
    play_time = models.PositiveSmallIntegerField("время партии, мин", default=60)
    image = models.ImageField("изображение", upload_to="games/", blank=True)
    image_url = models.URLField("ссылка на изображение", blank=True)
    price = models.DecimalField("стоимость игры, руб.", max_digits=9, decimal_places=2, default=0)
    price_url = models.URLField("страница игры в Hobby Games", blank=True)
    price_manual = models.BooleanField("цена задана вручную", default=False,
                                       help_text="Если отмечено, парсер не меняет цену")
    price_updated = models.DateTimeField("цена обновлена", null=True, blank=True)
    copies = models.PositiveSmallIntegerField("экземпляров в антикафе", default=1)
    tesera_id = models.PositiveIntegerField("номер игры на Tesera", null=True, blank=True, unique=True)
    age_min = models.PositiveSmallIntegerField("возраст от", null=True, blank=True)
    year = models.PositiveSmallIntegerField("год выпуска", null=True, blank=True)
    is_expansion = models.BooleanField("дополнение", default=False)
    plays_month = models.PositiveIntegerField("партий за месяц", default=0)
    plays_total = models.PositiveIntegerField("партий всего", default=0)

    class Meta:
        verbose_name = "настольная игра"
        verbose_name_plural = "настольные игры"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("games:detail", args=[self.pk])

    @property
    def rent_price(self):
        """Стоимость аренды за сутки — процент от цены игры (по умолчанию 10)."""
        value = self.price * Decimal(settings.RENT_PERCENT_PER_DAY) / 100
        return value.quantize(Decimal("1"))

    def tesera_url(self):
        return f"https://tesera.ru/game/{self.tesera_id}/" if self.tesera_id else ""

    def image_src(self):
        return self.image.url if self.image else self.image_url

    def available_copies(self):
        return self.copies - self.rentals.filter(returned_at__isnull=True,
                                                 status=Rental.Status.ISSUED).count()

    def avg_rating(self):
        return self.reviews.aggregate(models.Avg("rating"))["rating__avg"]

    def players_text(self):
        if self.players_min == self.players_max:
            return str(self.players_min)
        return f"{self.players_min}–{self.players_max}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    game = models.ForeignKey(BoardGame, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField("оценка", choices=[(i, str(i)) for i in range(1, 6)])
    text = models.TextField("отзыв", blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"
        ordering = ["-created"]
        unique_together = ("user", "game")


class Rental(models.Model):
    """Аренда настолки на дом. Первая аренда пользователя — только самовывоз."""

    class Method(models.TextChoices):
        PICKUP = "pickup", "Самовывоз"
        DELIVERY = "delivery", "Доставка"

    class Status(models.TextChoices):
        NEW = "new", "Заявка"
        ISSUED = "issued", "Выдана"
        RETURNED = "returned", "Возвращена"
        CANCELED = "canceled", "Отменена"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rentals")
    game = models.ForeignKey(BoardGame, on_delete=models.PROTECT, related_name="rentals")
    method = models.CharField("способ получения", max_length=10, choices=Method.choices, default=Method.PICKUP)
    contact_name = models.CharField("имя", max_length=100)
    phone = models.CharField("телефон", max_length=20)
    address = models.CharField("адрес доставки", max_length=200, blank=True)
    date_from = models.DateField("взять с")
    date_to = models.DateField("вернуть до")
    returned_at = models.DateField("фактически вернули", null=True, blank=True)
    amount = models.DecimalField("сумма, руб.", max_digits=9, decimal_places=2, default=0)
    paid = models.BooleanField("оплачено", default=False)
    status = models.CharField("статус", max_length=10, choices=Status.choices, default=Status.NEW)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "аренда игры"
        verbose_name_plural = "аренды игр"
        ordering = ["-created"]

    def __str__(self):
        return f"{self.game} — {self.user}"

    @property
    def days(self):
        return (self.date_to - self.date_from).days + 1

    def returned_on_time(self):
        if self.returned_at is None:
            return None
        return self.returned_at <= self.date_to

    @staticmethod
    def is_first_for(user):
        return not Rental.objects.filter(user=user).exclude(status=Rental.Status.CANCELED).exists()


class Console(models.Model):
    class Generation(models.TextChoices):
        RETRO = "retro", "Ретро-консоли"
        MODERN = "modern", "PS4 и Xbox 360"

    name = models.CharField("название", max_length=100)
    generation = models.CharField("раздел", max_length=10, choices=Generation.choices)
    description = models.TextField("краткий обзор", blank=True)
    image_url = models.URLField("ссылка на изображение", blank=True)

    class Meta:
        verbose_name = "консоль"
        verbose_name_plural = "консоли"
        ordering = ["generation", "name"]

    def __str__(self):
        return self.name


class ConsoleGame(models.Model):
    console = models.ForeignKey(Console, on_delete=models.CASCADE, related_name="games", verbose_name="консоль")
    title = models.CharField("название", max_length=150)
    genre = models.CharField("жанр", max_length=60, blank=True)
    review = models.TextField("краткая рецензия", blank=True)

    class Meta:
        verbose_name = "консольная игра"
        verbose_name_plural = "консольные игры"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.console})"
