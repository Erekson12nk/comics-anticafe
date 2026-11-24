"""Панель администратора: то, что неудобно делать в стандартной админке Django."""
import datetime as dt
import json
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from booking.models import Booking, Payment, Room
from games.models import BoardGame, Rental
from news.stats import publish_monthly_top

from .models import MoneyEntry


@staff_member_required
def dashboard(request):
    today = timezone.localdate()
    return render(request, "panel/dashboard.html", {
        "bookings_today": Booking.objects.filter(start__date=today).exclude(status=Booking.Status.CANCELED)
                                         .select_related("room", "user"),
        "rentals_open": Rental.objects.filter(status__in=[Rental.Status.NEW, Rental.Status.ISSUED]).count(),
        "rentals_late": Rental.objects.filter(status=Rental.Status.ISSUED, date_to__lt=today).count(),
    })


class MoneyForm(forms.ModelForm):
    class Meta:
        model = MoneyEntry
        fields = ["date", "kind", "amount", "note"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


@staff_member_required
def income(request):
    """Калькулятор доходности: онлайн-платежи считаются сами, остальное вносится вручную."""
    try:
        month = dt.date.fromisoformat(request.GET.get("m", "") + "-01")
    except ValueError:
        month = timezone.localdate().replace(day=1)
    next_month = (month + dt.timedelta(days=32)).replace(day=1)

    form = MoneyForm(request.POST or None, initial={"date": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Запись добавлена.")
        return redirect(f"{request.path}?m={month:%Y-%m}")

    paid = Payment.objects.filter(status=Payment.Status.SUCCEEDED,
                                  created__date__gte=month, created__date__lt=next_month)
    online = {k: paid.filter(kind=k).aggregate(s=Sum("amount"))["s"] or Decimal(0) for k, _ in Payment.Kind.choices}
    entries = MoneyEntry.objects.filter(date__gte=month, date__lt=next_month)
    manual_in = entries.filter(kind=MoneyEntry.Kind.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal(0)
    manual_out = entries.filter(kind=MoneyEntry.Kind.EXPENSE).aggregate(s=Sum("amount"))["s"] or Decimal(0)
    total_in = sum(online.values()) + manual_in
    profit = total_in - manual_out
    chart = {"labels": ["Проходки", "Бронирования", "Аренда игр", "Прочие доходы", "Расходы"],
             "values": [float(online["passes"]), float(online["booking"]), float(online["rental"]),
                        float(manual_in), float(manual_out)]}
    return render(request, "panel/income.html", {
        "form": form, "month": month, "online": online, "entries": entries,
        "manual_in": manual_in, "manual_out": manual_out, "total_in": total_in, "profit": profit,
        "margin": round(profit / total_in * 100) if total_in else 0,
        "prev": (month - dt.timedelta(days=1)).replace(day=1), "next": next_month,
        "chart_json": json.dumps(chart, ensure_ascii=False),
    })


@staff_member_required
def rentals(request):
    """Таблица аренд: кто, когда взял, вернул ли, вовремя ли заплатил."""
    status = request.GET.get("status", "")
    qs = Rental.objects.select_related("game", "user")
    if status:
        qs = qs.filter(status=status)
    return render(request, "panel/rentals.html", {
        "rentals": qs[:200], "status": status, "statuses": Rental.Status.choices,
        "today": timezone.localdate()})


@staff_member_required
@require_POST
def rental_action(request, pk):
    rental = get_object_or_404(Rental, pk=pk)
    action = request.POST.get("action")
    if action == "issue":
        rental.status = Rental.Status.ISSUED
    elif action == "return":
        rental.status = Rental.Status.RETURNED
        rental.returned_at = timezone.localdate()
    elif action == "paid":
        rental.paid = True
    elif action == "cancel":
        rental.status = Rental.Status.CANCELED
    rental.save()
    return redirect(request.POST.get("next") or "panel:rentals")


@staff_member_required
def plays(request):
    """Счетчик заигранности: администратор отмечает каждую сыгранную партию."""
    q = request.GET.get("q", "")
    games = BoardGame.objects.all()
    if q:
        games = games.filter(title__icontains=q)
    return render(request, "panel/plays.html", {"games": games.order_by("-plays_month", "title"), "q": q})


@staff_member_required
@require_POST
def play_count(request, pk):
    delta = 1 if request.POST.get("d") != "-1" else -1
    game = get_object_or_404(BoardGame, pk=pk)
    if delta < 0 and game.plays_month == 0:
        return redirect(request.POST.get("next") or "panel:plays")
    BoardGame.objects.filter(pk=pk).update(plays_month=F("plays_month") + delta, plays_total=F("plays_total") + delta)
    return redirect(request.POST.get("next") or "panel:plays")


@staff_member_required
@require_POST
def publish_top(request):
    news = publish_monthly_top(author=request.user)
    if news:
        messages.success(request, "Топ-15 опубликован в новостях, счетчики обнулены.")
    else:
        messages.info(request, "За месяц еще нет сыгранных партий.")
    return redirect("panel:plays")


@staff_member_required
def map_edit(request):
    """Редактор карты: комнаты перетаскиваются мышью, размеры и цвет меняются в полях."""
    if request.method == "POST":
        data = json.loads(request.body)
        for item in data.get("rooms", []):
            Room.objects.filter(pk=item["id"]).update(
                x=max(0, int(item["x"])), y=max(0, int(item["y"])),
                width=max(40, int(item["width"])), height=max(40, int(item["height"])),
                color=item.get("color", "#3b82f6")[:7], name=item.get("name", "")[:60] or "Комната")
        return JsonResponse({"ok": True})
    rooms = [{"id": r.pk, "name": r.name, "x": r.x, "y": r.y, "width": r.width, "height": r.height,
              "color": r.color} for r in Room.objects.all()]
    return render(request, "panel/map_edit.html", {"rooms": rooms})
