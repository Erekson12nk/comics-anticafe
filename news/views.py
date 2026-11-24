import json

from django.shortcuts import render
from django.utils import timezone

from booking.models import Event
from games.models import BoardGame

from .models import News


def news_list(request):
    """Новости и статистика: лента администратора + график самых популярных игр."""
    kind = request.GET.get("kind", "")
    items = News.objects.all()
    if kind:
        items = items.filter(kind=kind)
    top = list(BoardGame.objects.filter(plays_total__gt=0).order_by("-plays_total")[:15])
    chart = {"labels": [g.title for g in top], "month": [g.plays_month for g in top],
             "total": [g.plays_total for g in top]}
    return render(request, "news/list.html", {
        "items": items[:30], "kind": kind, "kinds": News.Kind.choices,
        "chart_json": json.dumps(chart, ensure_ascii=False),
        "big_events": Event.objects.filter(is_big=True, end__gte=timezone.now()).order_by("start")[:3],
    })
