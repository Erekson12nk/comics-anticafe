import datetime as dt

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.achievements import check_all
from booking.models import Payment

from .models import BoardGame, Console, Rental, Review


def recommendations(game=None, user=None, limit=4):
    """Простая система рекомендаций: игры того же жанра и с подходящим числом игроков,
    а для пользователя — игры жанров из его избранного. Сначала самые популярные."""
    qs = BoardGame.objects.filter(is_expansion=False)
    if game:
        qs = qs.filter(genre=game.genre, players_max__gte=game.players_min,
                       players_min__lte=game.players_max).exclude(pk=game.pk)
    elif user and user.is_authenticated:
        fav = user.profile.favorites.all()
        genres = set(fav.values_list("genre", flat=True))
        if not genres:
            return []
        qs = qs.filter(genre__in=genres).exclude(pk__in=fav)
    return list(qs.order_by("-plays_total", "title")[:limit])


def catalog(request):
    """Каталог настольных игр с поиском и фильтрами."""
    games = BoardGame.objects.annotate(n_reviews=Count("reviews"))
    q = request.GET.get("q", "").strip()
    genre = request.GET.get("genre", "")
    players = request.GET.get("players", "")
    sort = request.GET.get("sort", "title")
    with_expansions = request.GET.get("exp") == "1"
    if not with_expansions and genre != "дополнение":
        games = games.filter(is_expansion=False)
    if q:
        games = games.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if genre:
        games = games.filter(genre=genre)
    if players.isdigit():
        games = games.filter(players_min__lte=int(players), players_max__gte=int(players))
    games = games.order_by({"popular": "-plays_total", "price": "price"}.get(sort, "title"))
    favorites = set()
    if request.user.is_authenticated:
        favorites = set(request.user.profile.favorites.values_list("pk", flat=True))
    page = Paginator(games, 24).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "games/catalog.html", {
        "games": page, "page": page, "query": params.urlencode(), "total": page.paginator.count,
        "q": q, "genre": genre, "players": players, "sort": sort, "with_expansions": with_expansions,
        "genres": BoardGame.objects.exclude(genre="").values_list("genre", flat=True).distinct().order_by("genre"),
        "favorites": favorites,
        "recommended": recommendations(user=request.user),
    })


class BootstrapMixin:
    """Добавляет полям классы Bootstrap, чтобы формы выглядели одинаково."""

    def style_fields(self):
        for f in self.fields.values():
            f.widget.attrs["class"] = "form-select" if isinstance(f.widget, forms.Select) else "form-control"


class RentalForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Rental
        fields = ["method", "contact_name", "phone", "address", "date_from", "date_to"]
        widgets = {"date_from": forms.DateInput(attrs={"type": "date"}),
                   "date_to": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.style_fields()
        if user is not None and Rental.is_first_for(user):
            self.fields["method"].choices = [(Rental.Method.PICKUP, "Самовывоз (первая аренда — только самовывоз)")]

    def clean(self):
        data = super().clean()
        today = timezone.localdate()
        d1, d2 = data.get("date_from"), data.get("date_to")
        if d1 and d2:
            if d1 < today:
                self.add_error("date_from", "Дата уже прошла.")
            if d2 < d1:
                self.add_error("date_to", "Дата возврата раньше даты получения.")
            elif (d2 - d1).days > 13:
                self.add_error("date_to", "Аренда — не больше двух недель.")
        if data.get("method") == Rental.Method.DELIVERY:
            if self.user is not None and Rental.is_first_for(self.user):
                self.add_error("method", "Первая аренда — только самовывоз.")
            if not data.get("address"):
                self.add_error("address", "Укажите адрес доставки.")
        return data


class ReviewForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 2, "placeholder": "Как вам игра?"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


def detail(request, pk):
    game = get_object_or_404(BoardGame, pk=pk)
    user = request.user
    rental_form = review_form = None
    if user.is_authenticated:
        today = timezone.localdate()
        rental_form = RentalForm(user=user, initial={
            "contact_name": user.get_full_name() or user.username, "phone": user.profile.phone,
            "date_from": today, "date_to": today + dt.timedelta(days=1)})
        review_form = ReviewForm()
    return render(request, "games/detail.html", {
        "game": game, "reviews": game.reviews.select_related("user__profile"),
        "rental_form": rental_form, "review_form": review_form,
        "is_favorite": user.is_authenticated and user.profile.favorites.filter(pk=pk).exists(),
        "similar": recommendations(game=game),
        "first_rental": user.is_authenticated and Rental.is_first_for(user),
    })


@login_required
@require_POST
def rent(request, pk):
    """Бронирование настолки на дом: доставка или самовывоз, контакты, оплата."""
    game = get_object_or_404(BoardGame, pk=pk)
    form = RentalForm(request.POST, user=request.user)
    if not form.is_valid():
        for errors in form.errors.values():
            for e in errors:
                messages.error(request, e)
        return redirect(game)
    if game.available_copies() <= 0:
        messages.error(request, "Все экземпляры этой игры сейчас на руках.")
        return redirect(game)
    rental = form.save(commit=False)
    rental.user, rental.game = request.user, game
    rental.amount = game.rent_price * rental.days
    rental.save()
    check_all(request.user)
    payment = Payment.objects.create(user=request.user, kind=Payment.Kind.RENTAL,
                                     amount=rental.amount, rental=rental)
    return redirect("booking:pay", payment.pk)


@login_required
@require_POST
def review(request, pk):
    game = get_object_or_404(BoardGame, pk=pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        Review.objects.update_or_create(user=request.user, game=game, defaults=form.cleaned_data)
        check_all(request.user)
        messages.success(request, "Спасибо за отзыв!")
    return redirect(game)


@login_required
@require_POST
def toggle_favorite(request, pk):
    game = get_object_or_404(BoardGame, pk=pk)
    favs = request.user.profile.favorites
    if favs.filter(pk=pk).exists():
        favs.remove(game)
    else:
        favs.add(game)
    return redirect(request.POST.get("next") or game.get_absolute_url())


def consoles(request):
    """Каталог консольных игр: ретро и PS4 / Xbox 360."""
    sections = []
    for code, label in Console.Generation.choices:
        sections.append((code, label, Console.objects.filter(generation=code).prefetch_related("games")))
    return render(request, "games/consoles.html", {"sections": sections})
