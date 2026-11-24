from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Дополнительные данные пользователя: аватар, контакты, проходки, избранное."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField("аватар", upload_to="avatars/", blank=True)
    avatar_url = models.URLField("аватар из VK", blank=True)
    phone = models.CharField("телефон", max_length=20, blank=True)
    passes = models.PositiveIntegerField("купленные проходки", default=0)
    favorites = models.ManyToManyField("games.BoardGame", blank=True, related_name="fans",
                                       verbose_name="избранные настолки")

    class Meta:
        verbose_name = "профиль"
        verbose_name_plural = "профили"

    def __str__(self):
        return f"Профиль {self.user}"

    def avatar_src(self):
        if self.avatar:
            return self.avatar.url
        return self.avatar_url or ""

    def display_name(self):
        return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class Achievement(models.Model):
    """Заготовка системы ачивок: администратор заводит достижения, выдача — в accounts/achievements.py."""
    code = models.SlugField("код", unique=True)
    title = models.CharField("название", max_length=100)
    description = models.CharField("как получить", max_length=200)
    icon = models.CharField("значок (эмодзи)", max_length=8, default="🏆")
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="achievements")

    class Meta:
        verbose_name = "достижение"
        verbose_name_plural = "достижения"

    def __str__(self):
        return self.title
