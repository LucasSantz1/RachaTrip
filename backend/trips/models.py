import uuid

from django.db import models
from django.db.models import CharField, F, Q
from django.db.models.functions import Length

from trips.ledger import MAX_AMOUNT_CENTS

CharField.register_lookup(Length)  # habilita Q(campo__length__gte=...) nas constraints

MAX_PARTICIPANTS_PER_TRIP = 50  # validado na API (Marco 2)


class Category(models.TextChoices):
    TRANSPORTE = "transporte", "Transporte"
    HOSPEDAGEM = "hospedagem", "Hospedagem"
    ALIMENTACAO = "alimentacao", "Alimentação"
    MERCADO = "mercado", "Mercado"
    PASSEIOS = "passeios", "Passeios"
    OUTROS = "outros", "Outros"


class Trip(models.Model):
    public_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    destination = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    admin_token_hash = models.CharField(max_length=64, unique=True)
    share_token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="trip_end_after_start",
            ),
            models.CheckConstraint(condition=Q(name__length__gte=1), name="trip_name_not_empty"),
            models.CheckConstraint(
                condition=Q(admin_token_hash__regex=r"^[0-9a-f]{64}$"),  # noqa: S106 (não é senha)
                name="trip_admin_token_hash_format",
            ),
            models.CheckConstraint(
                condition=Q(share_token_hash__regex=r"^[0-9a-f]{64}$"),  # noqa: S106 (não é senha)
                name="trip_share_token_hash_format",
            ),
        ]

    def __str__(self):
        return self.name


class Participant(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="participants")
    name = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "name"],
                name="participant_unique_name_per_trip",
            ),
            models.CheckConstraint(
                condition=Q(name__length__gte=1), name="participant_name_not_empty"
            ),
        ]

    def __str__(self):
        return self.name


class Expense(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=120)
    amount_cents = models.IntegerField()
    category = models.CharField(max_length=20, choices=Category.choices)
    date = models.DateField()
    payer = models.ForeignKey(Participant, on_delete=models.RESTRICT, related_name="paid_expenses")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["trip", "-date", "-id"], name="expense_trip_date_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(category__in=Category.values), name="expense_category_valid"
            ),
            models.CheckConstraint(
                condition=Q(description__length__gte=1), name="expense_description_not_empty"
            ),
            models.CheckConstraint(
                condition=Q(amount_cents__gte=1) & Q(amount_cents__lte=MAX_AMOUNT_CENTS),
                name="expense_amount_range",
            ),
        ]

    def __str__(self):
        return self.description


class ExpenseShare(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="shares")
    participant = models.ForeignKey(
        Participant, on_delete=models.RESTRICT, related_name="expense_shares"
    )

    class Meta:
        # split_equal distribui os centavos que sobram pela ordem de cadastro;
        # a ordem das partes precisa ser determinística.
        ordering = ["participant_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["expense", "participant"],
                name="share_unique_participant",
            ),
        ]
