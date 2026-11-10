import datetime

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.models import RestrictedError

from trips.ledger import MAX_AMOUNT_CENTS
from trips.models import (
    MAX_PARTICIPANTS_PER_TRIP,
    Category,
    Expense,
    ExpenseShare,
    Participant,
    Trip,
)

pytestmark = pytest.mark.django_db

mysql_only = pytest.mark.skipif(
    connection.vendor != "mysql",
    reason="depende da collation utf8mb4_0900_ai_ci do MySQL",
)

_counter = iter(range(1, 10_000))


def make_trip(**kwargs):
    n = next(_counter)
    defaults = {
        "name": "Praia",
        "start_date": datetime.date(2026, 1, 10),
        "end_date": datetime.date(2026, 1, 15),
        "admin_token_hash": f"a{n}".ljust(64, "0"),
        "share_token_hash": f"s{n}".ljust(64, "0"),
    }
    defaults.update(kwargs)
    return Trip.objects.create(**defaults)


def make_expense(trip, payer, amount_cents=1000):
    return Expense.objects.create(
        trip=trip,
        description="Jantar",
        amount_cents=amount_cents,
        category=Category.ALIMENTACAO,
        date=datetime.date(2026, 1, 11),
        payer=payer,
    )


def test_constants_and_categories():
    assert MAX_PARTICIPANTS_PER_TRIP == 50
    assert Category.TRANSPORTE.value == "transporte"
    assert [c.value for c in Category] == [
        "transporte",
        "hospedagem",
        "alimentacao",
        "mercado",
        "passeios",
        "outros",
    ]
    assert Category.ALIMENTACAO.label == "Alimentação"


def test_end_before_start_rejected():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_trip(start_date=datetime.date(2026, 1, 10), end_date=datetime.date(2026, 1, 9))


def test_same_day_trip_allowed():
    make_trip(start_date=datetime.date(2026, 1, 10), end_date=datetime.date(2026, 1, 10))


@pytest.mark.parametrize("amount", [0, MAX_AMOUNT_CENTS + 1])
def test_amount_out_of_range_rejected(amount):
    trip = make_trip()
    payer = Participant.objects.create(trip=trip, name="Ana")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_expense(trip, payer, amount)


@pytest.mark.parametrize("amount", [1, MAX_AMOUNT_CENTS])
def test_amount_in_range_saved(amount):
    trip = make_trip()
    payer = Participant.objects.create(trip=trip, name="Ana")
    assert make_expense(trip, payer, amount).pk is not None


def test_duplicate_participant_name_same_trip_rejected():
    trip = make_trip()
    Participant.objects.create(trip=trip, name="Ana")
    with pytest.raises(IntegrityError), transaction.atomic():
        Participant.objects.create(trip=trip, name="Ana")


@mysql_only
def test_participant_name_case_insensitive_collision():
    trip = make_trip()
    Participant.objects.create(trip=trip, name="Ana")
    with pytest.raises(IntegrityError), transaction.atomic():
        Participant.objects.create(trip=trip, name="ana")


def test_same_participant_name_in_different_trips_allowed():
    Participant.objects.create(trip=make_trip(), name="Ana")
    Participant.objects.create(trip=make_trip(), name="Ana")


def test_emoji_name_roundtrip():
    trip = make_trip()
    p = Participant.objects.create(trip=trip, name="Zé 🚗")
    p.refresh_from_db()
    assert p.name == "Zé 🚗"
    assert Participant.objects.get(pk=p.pk).name == "Zé 🚗"


def test_participants_ordered_by_id():
    trip = make_trip()
    b = Participant.objects.create(trip=trip, name="Beto")
    a = Participant.objects.create(trip=trip, name="Ana")
    assert list(trip.participants.all()) == [b, a]


def test_duplicate_admin_token_hash_rejected():
    make_trip(admin_token_hash="x" * 64)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_trip(admin_token_hash="x" * 64)


def test_duplicate_share_token_hash_rejected():
    make_trip(share_token_hash="y" * 64)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_trip(share_token_hash="y" * 64)


def test_duplicate_share_rejected():
    trip = make_trip()
    ana = Participant.objects.create(trip=trip, name="Ana")
    expense = make_expense(trip, ana)
    ExpenseShare.objects.create(expense=expense, participant=ana)
    with pytest.raises(IntegrityError), transaction.atomic():
        ExpenseShare.objects.create(expense=expense, participant=ana)


def test_delete_trip_cascades():
    trip = make_trip()
    ana = Participant.objects.create(trip=trip, name="Ana")
    beto = Participant.objects.create(trip=trip, name="Beto")
    expense = make_expense(trip, ana)
    ExpenseShare.objects.create(expense=expense, participant=ana)
    ExpenseShare.objects.create(expense=expense, participant=beto)
    trip.delete()
    assert not Participant.objects.exists()
    assert not Expense.objects.exists()
    assert not ExpenseShare.objects.exists()


def test_delete_payer_restricted():
    trip = make_trip()
    ana = Participant.objects.create(trip=trip, name="Ana")
    make_expense(trip, ana)
    with pytest.raises(RestrictedError), transaction.atomic():
        ana.delete()


def test_delete_participant_in_share_restricted():
    trip = make_trip()
    ana = Participant.objects.create(trip=trip, name="Ana")
    beto = Participant.objects.create(trip=trip, name="Beto")
    expense = make_expense(trip, ana)
    ExpenseShare.objects.create(expense=expense, participant=beto)
    with pytest.raises(RestrictedError), transaction.atomic():
        beto.delete()


def test_public_id_auto_and_unique():
    a, b = make_trip(), make_trip()
    assert a.public_id is not None
    assert a.public_id != b.public_id
