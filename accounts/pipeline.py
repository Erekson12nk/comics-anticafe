"""Шаг входа через VK: сохраняем ссылку на аватар пользователя из VK."""


def save_vk_avatar(backend, user, response, *args, **kwargs):
    photo = response.get("photo_200") or response.get("photo")
    if user and photo and not user.profile.avatar_url:
        user.profile.avatar_url = photo
        user.profile.save(update_fields=["avatar_url"])
