from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Achievement


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Имя", max_length=150)


class ProfileForm(forms.Form):
    first_name = forms.CharField(label="Имя", max_length=150, required=False)
    phone = forms.CharField(label="Телефон", max_length=20, required=False)
    avatar = forms.ImageField(label="Аватар", required=False)


def register(request):
    """Регистрация по логину и паролю — запасной вариант, если вход через VK не настроен."""
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.first_name = form.cleaned_data["first_name"]
        user.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("accounts:profile")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    user = request.user
    prof = user.profile
    form = ProfileForm(request.POST or None, request.FILES or None,
                       initial={"first_name": user.first_name, "phone": prof.phone})
    if request.method == "POST" and form.is_valid():
        user.first_name = form.cleaned_data["first_name"]
        user.save(update_fields=["first_name"])
        prof.phone = form.cleaned_data["phone"]
        if form.cleaned_data["avatar"]:
            prof.avatar = form.cleaned_data["avatar"]
        prof.save()
        messages.success(request, "Профиль сохранен.")
        return redirect("accounts:profile")

    today = timezone.localdate()
    return render(request, "accounts/profile.html", {
        "form": form,
        "prof": prof,
        "achievements": Achievement.objects.all(),
        "my_achievements": set(user.achievements.values_list("pk", flat=True)),
        "bookings": user.bookings.filter(end__gte=timezone.now()).select_related("room"),
        "rentals": user.rentals.select_related("game")[:10],
        "visits": user.visits.filter(date__gte=today).select_related("game"),
        "favorites": prof.favorites.all(),
        "events": user.events_joined.filter(end__gte=timezone.now()),
    })
