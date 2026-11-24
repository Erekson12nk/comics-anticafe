from django.db import models


class MoneyEntry(models.Model):
    """Ручная запись для калькулятора доходности (доход или расход)."""

    class Kind(models.TextChoices):
        INCOME = "income", "Доход"
        EXPENSE = "expense", "Расход"

    date = models.DateField("дата")
    kind = models.CharField("тип", max_length=10, choices=Kind.choices)
    amount = models.DecimalField("сумма, руб.", max_digits=10, decimal_places=2)
    note = models.CharField("за что", max_length=150)

    class Meta:
        verbose_name = "запись доходов и расходов"
        verbose_name_plural = "доходы и расходы"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount} — {self.note}"
