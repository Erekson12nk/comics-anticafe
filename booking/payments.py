"""
Онлайн-оплата через ЮKassa.

Если в настройках заданы YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY, платеж создается в ЮKassa и
пользователь уходит на ее страницу оплаты. Если ключей нет — включается демо-режим:
на сайте показывается кнопка «Оплатить (демо)», которая сразу отмечает платеж оплаченным.
"""
import uuid

import requests
from django.conf import settings
from django.db import transaction

from accounts.achievements import check_all

from .models import Booking, Payment

API_URL = "https://api.yookassa.ru/v3/payments"


def yookassa_enabled():
    return bool(settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY)


def create_yookassa_payment(payment, return_url):
    """Создать платеж в ЮKassa и вернуть ссылку на страницу оплаты."""
    resp = requests.post(
        API_URL,
        auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        headers={"Idempotence-Key": str(uuid.uuid4())},
        json={
            "amount": {"value": f"{payment.amount:.2f}", "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": f"Com!cs: {payment.get_kind_display()} (заказ {payment.pk})",
            "metadata": {"payment_id": payment.pk},
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    payment.external_id = data["id"]
    payment.save(update_fields=["external_id"])
    return data["confirmation"]["confirmation_url"]


def check_yookassa_status(payment):
    """Узнать в ЮKassa, оплачен ли платеж (вызывается при возврате пользователя и из уведомления)."""
    resp = requests.get(f"{API_URL}/{payment.external_id}",
                        auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY), timeout=15)
    resp.raise_for_status()
    return resp.json()["status"]


@transaction.atomic
def mark_paid(payment):
    """Отметить платеж оплаченным и применить его: начислить проходки, подтвердить бронь или аренду."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == Payment.Status.SUCCEEDED:
        return payment
    payment.status = Payment.Status.SUCCEEDED
    payment.save(update_fields=["status"])
    if payment.kind == Payment.Kind.PASSES:
        profile = payment.user.profile
        profile.passes += payment.quantity
        profile.save(update_fields=["passes"])
    if payment.booking:
        payment.booking.status = Booking.Status.PAID
        payment.booking.save(update_fields=["status"])
    if payment.rental:
        payment.rental.paid = True
        payment.rental.save(update_fields=["paid"])
    check_all(payment.user)
    return payment
