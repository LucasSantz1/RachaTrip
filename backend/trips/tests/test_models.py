import datetime
import hashlib
import secrets

import pytest
from django.db import DataError, IntegrityError, connection, transaction
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


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def make_trip(**kwargs):
    n = next(_counter)
    defaults = {
        "name": "Praia",
        "start_date": datetime.date(2026, 1, 10),
        "end_date": datetime.date(2026, 1, 15),
        "admin_token_hash": sha(f"admin{n}"),
        "share_token_hash": sha(f"share{n}"),
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
    make_trip(admin_token_hash=sha("dup"))
    with pytest.raises(IntegrityError), transaction.atomic():
        make_trip(admin_token_hash=sha("dup"))


def test_duplicate_share_token_hash_rejected():
    make_trip(share_token_hash=sha("dup"))
    with pytest.raises(IntegrityError), transaction.atomic():
        make_trip(share_token_hash=sha("dup"))


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
    other = make_trip()
    carla = Participant.objects.create(trip=other, name="Carla")
    other_expense = make_expense(other, carla)
    ExpenseShare.objects.create(expense=other_expense, participant=carla)
    trip.delete()
    assert list(Participant.objects.all()) == [carla]
    assert list(Expense.objects.all()) == [other_expense]
    assert ExpenseShare.objects.count() == 1


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


def test_empty_trip_name_rejected():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_trip(name="")


def test_empty_participant_name_rejected():
    with pytest.raises(IntegrityError), transaction.atomic():
        Participant.objects.create(trip=make_trip(), name="")


def test_empty_expense_description_rejected():
    trip = make_trip()
    payer = Participant.objects.create(trip=trip, name="Ana")
    with pytest.raises(IntegrityError), transaction.atomic():
        Expense.objects.create(
            trip=trip,
            description="",
            amount_cents=100,
            category=Category.OUTROS,
            date=datetime.date(2026, 1, 11),
            payer=payer,
        )


BAD_HASHES = ["x", "a" * 63, "A" * 64, "a" * 63 + "g", "a" * 65]


@pytest.mark.parametrize("field", ["admin_token_hash", "share_token_hash"])
@pytest.mark.parametrize("bad", BAD_HASHES)
def test_malformed_token_hash_rejected(field, bad):
    # 65 caracteres estoura o varchar(64): o MySQL estrito levanta DataError (1406).
    with pytest.raises((IntegrityError, DataError)), transaction.atomic():
        make_trip(**{field: bad})


@pytest.mark.parametrize("field", ["admin_token_hash", "share_token_hash"])
def test_raw_token_never_storable(field):
    # Um token cru (token_urlsafe) nunca pode virar hash armazenado.
    with pytest.raises((IntegrityError, DataError)), transaction.atomic():
        make_trip(**{field: secrets.token_urlsafe(32)})


def test_valid_sha256_hash_saved():
    trip = make_trip(admin_token_hash=sha("ok"), share_token_hash=sha("ok2"))
    assert trip.pk is not None


def test_invalid_category_rejected():
    trip = make_trip()
    payer = Participant.objects.create(trip=trip, name="Ana")
    with pytest.raises(IntegrityError), transaction.atomic():
        Expense.objects.create(
            trip=trip,
            description="x",
            amount_cents=100,
            category="invalida",
            date=datetime.date(2026, 1, 11),
            payer=payer,
        )


def test_expenses_ordered_newest_first():
    trip = make_trip()
    ana = Participant.objects.create(trip=trip, name="Ana")
    old = make_expense(trip, ana)
    new = make_expense(trip, ana)
    assert list(Expense.objects.all()) == [new, old]


def test_shares_ordered_by_participant_id():
    trip = make_trip()
    ana = Participant.objects.create(trip=trip, name="Ana")
    beto = Participant.objects.create(trip=trip, name="Beto")
    expense = make_expense(trip, ana)
    ExpenseShare.objects.create(expense=expense, participant=beto)
    ExpenseShare.objects.create(expense=expense, participant=ana)
    assert [s.participant_id for s in expense.shares.all()] == [ana.id, beto.id]
