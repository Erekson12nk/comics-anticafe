import datetime as dt
import json
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.achievements import check_all
from games.models import BoardGame

from . import payments
from .models import Booking, Event, Payment, Room, Visit


def _day_bounds(day):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(dt.datetime.combine(day, dt.time.min), tz)
    return start, start + dt.timedelta(days=1)


def map_view(request):
    """Главная страница: карта заведения на выбранный день."""
    today = timezone.localdate()
    try:
        day = dt.date.fromisoformat(request.GET.get("d", ""))
    except ValueError:
        day = today
    day = max(day, today)
    days = [today + dt.timedelta(days=i) for i in range(settings.BOOKING_DAYS_AHEAD)]
    too_far = day > days[-1]

    context = {"day": day, "days": days, "too_far": too_far, "today": today,
               "prev_day": day - dt.timedelta(days=1), "next_day": day + dt.timedelta(days=1)}
    if too_far:
        return render(request, "booking/map.html", context)

    start, end = _day_bounds(day)
    rooms = list(Room.objects.all())
    events = Event.objects.filter(start__lt=end, end__gt=start).select_related("template", "game", "room")
    bookings = Booking.objects.filter(start__lt=end, end__gt=start).exclude(status=Booking.Status.CANCELED)
    tz = timezone.get_current_timezone()
    for room in rooms:
        # Координаты строк внутри прямоугольника комнаты на SVG-карте
        room.event_rows = [(e, room.y + 62 + 60 * i) for i, e in
                           enumerate(e for e in events if e.room_id == room.pk)]
        busy = sorted([b for b in bookings if b.room_id == room.pk], key=lambda b: b.start)[:3]
        room.busy_rows = [(f"занято {b.start.astimezone(tz):%H:%M}–{b.end.astimezone(tz):%H:%M}",
                           room.y + room.height - 12 - 18 * i) for i, b in enumerate(busy)]
    visits = Visit.objects.filter(date=day).select_related("user__profile", "game")

    # Настолки, которые запланированы на вечер: из мероприятий и из планов гостей
    evening_games = {e.game for e in events if e.game} | {v.game for v in visits if v.game}

    my_visit = None
    if request.user.is_authenticated:
        my_visit = next((v for v in visits if v.user_id == request.user.pk), None)

    context.update({
        "rooms": rooms, "events": events, "visits": visits, "my_visit": my_visit,
        "evening_games": sorted(evening_games, key=lambda g: g.title),
        "games": BoardGame.objects.only("id", "title"),
        "purposes": Booking.Purpose.choices,
    })
    return render(request, "booking/map.html", context)


@login_required
@require_POST
def book_room(request, room_id):
    """Бронирование комнаты по нажатию на нее на карте."""
    room = get_object_or_404(Room, pk=room_id)
    try:
        day = dt.date.fromisoformat(request.POST["date"])
        time = dt.time.fromisoformat(request.POST["time"])
        hours = int(request.POST.get("hours", 2))
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Неверные дата или время")
    today = timezone.localdate()
    if not (today <= day < today + dt.timedelta(days=settings.BOOKING_DAYS_AHEAD)) or not 1 <= hours <= 12:
        messages.error(request, "Бронировать можно только на ближайшие две недели и от 1 до 12 часов.")
        return redirect(f"{reverse('booking:map')}?d={day}")

    start = timezone.make_aware(dt.datetime.combine(day, time))
    booking = Booking(user=request.user, room=room, start=start, end=start + dt.timedelta(hours=hours),
                      purpose=request.POST.get("purpose", Booking.Purpose.CHILL),
                      comment=request.POST.get("comment", "")[:200],
                      amount=room.price_hour * hours)
    try:
        booking.full_clean()
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
        return redirect(f"{reverse('booking:map')}?d={day}")
    booking.save()
    payment = Payment.objects.create(user=request.user, kind=Payment.Kind.BOOKING,
                                     amount=booking.amount, booking=booking)
    return redirect("booking:pay", payment.pk)


@login_required
@require_POST
def plan_visit(request):
    """Отметить планируемую дату прихода (с предпочтительной игрой и комментарием) или убрать отметку."""
    try:
        day = dt.date.fromisoformat(request.POST["date"])
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Неверная дата")
    if request.POST.get("remove"):
        Visit.objects.filter(user=request.user, date=day).delete()
        messages.info(request, "Отметка о визите удалена.")
    else:
        game_id = request.POST.get("game") or None
        Visit.objects.update_or_create(user=request.user, date=day, defaults={
            "game_id": game_id, "comment": request.POST.get("comment", "")[:150]})
        messages.success(request, "Вы отметились на карте — другие гости увидят, что вы придете.")
    return redirect(f"{reverse('booking:map')}?d={day}")


def events_view(request):
    """Календарь мероприятий."""
    now = timezone.now()
    events = Event.objects.filter(end__gte=now).select_related("template", "room", "game")
    return render(request, "booking/events.html", {"events": events})


@login_required
@require_POST
def toggle_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if event.participants.filter(pk=request.user.pk).exists():
        event.participants.remove(request.user)
        messages.info(request, f"Вы отписались от «{event.title}».")
    elif event.free_seats() > 0:
        event.participants.add(request.user)
        check_all(request.user)
        messages.success(request, f"Вы записаны на «{event.title}».")
    else:
        messages.error(request, "Свободных мест нет.")
    return redirect("booking:events")


@login_required
@require_POST
def buy_passes(request):
    try:
        qty = max(1, min(int(request.POST.get("quantity", 1)), 20))
    except ValueError:
        qty = 1
    payment = Payment.objects.create(user=request.user, kind=Payment.Kind.PASSES,
                                     amount=Decimal(settings.PASS_PRICE) * qty, quantity=qty)
    return redirect("booking:pay", payment.pk)


@login_required
def pay(request, payment_id):
    """Страница оплаты: переход в ЮKassa или демо-оплата."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
    if payment.status == Payment.Status.SUCCEEDED:
        return render(request, "booking/pay.html", {"payment": payment, "done": True})
    if payments.yookassa_enabled():
        if payment.external_id and payments.check_yookassa_status(payment) == "succeeded":
            payments.mark_paid(payment)
            return render(request, "booking/pay.html", {"payment": payment, "done": True})
        if request.method == "POST":
            url = payments.create_yookassa_payment(
                payment, request.build_absolute_uri(reverse("booking:pay", args=[payment.pk])))
            return redirect(url)
    elif request.method == "POST":
        payments.mark_paid(payment)
        messages.success(request, "Оплата прошла (демо-режим).")
        return redirect("booking:pay", payment.pk)
    return render(request, "booking/pay.html", {"payment": payment, "demo": not payments.yookassa_enabled()})


@csrf_exempt
@require_POST
def yookassa_webhook(request):
    """Уведомление от ЮKassa. Статус перепроверяется запросом к API, поэтому подделать его нельзя."""
    try:
        obj = json.loads(request.body)["object"]
        payment = Payment.objects.get(external_id=obj["id"])
    except (ValueError, KeyError, Payment.DoesNotExist):
        return HttpResponse(status=200)
    if payments.check_yookassa_status(payment) == "succeeded":
        payments.mark_paid(payment)
    return HttpResponse(status=200)
