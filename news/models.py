from django.conf import settings
from django.db import models


class News(models.Model):
    class Kind(models.TextChoices):
        NEWS = "news", "Новинки"
        STATS = "stats", "Статистика"
        IDEAS = "ideas", "Идеи и планы"

    title = models.CharField("заголовок", max_length=150)
    text = models.TextField("текст")
    kind = models.CharField("рубрика", max_length=10, choices=Kind.choices, default=Kind.NEWS)
    image = models.ImageField("картинка", upload_to="news/", blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField("опубликовано", auto_now_add=True)

    class Meta:
        verbose_name = "новость"
        verbose_name_plural = "новости"
        ordering = ["-created"]

    def __str__(self):
        return self.title
