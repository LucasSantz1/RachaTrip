import random
from decimal import Decimal

import pytest

from trips.ledger import MAX_AMOUNT_CENTS, LedgerError, split_equal, validate_amount_cents


@pytest.mark.parametrize("value", [1, 1234, MAX_AMOUNT_CENTS])
def test_accepts_valid_cents(value):
    assert validate_amount_cents(value) == value


@pytest.mark.parametrize("value", [True, False, 12.0, 12.5, "1234", None, Decimal("12")])
def test_rejects_non_int(value):
    with pytest.raises(LedgerError) as e:
        validate_amount_cents(value)
    assert e.value.code == "amount_not_integer"
    if value == "1234":
        assert "1234" not in str(e.value)


@pytest.mark.parametrize("value", [0, -1, MAX_AMOUNT_CENTS + 1])
def test_rejects_out_of_range(value):
    with pytest.raises(LedgerError) as e:
        validate_amount_cents(value)
    assert e.value.code == "amount_out_of_range"


def test_split_equal_distributes_remainder_in_order():
    assert split_equal(10000, [1, 2, 3]) == {1: 3334, 2: 3333, 3: 3333}


def test_split_equal_one_cent_goes_to_first():
    assert split_equal(1, [7, 8, 9]) == {7: 1, 8: 0, 9: 0}


def test_split_equal_single_participant():
    assert split_equal(500, [4]) == {4: 500}


def test_split_equal_rejects_empty():
    with pytest.raises(LedgerError) as e:
        split_equal(100, [])
    assert e.value.code == "split_empty"


def test_split_equal_rejects_duplicates():
    with pytest.raises(LedgerError) as e:
        split_equal(100, [1, 1])
    assert e.value.code == "split_duplicate"


def test_split_equal_rejects_zero_total():
    with pytest.raises(LedgerError) as e:
        split_equal(0, [1])
    assert e.value.code == "amount_out_of_range"


def test_split_equal_properties_random():
    rng = random.Random(20261110)  # noqa: S311 - PRNG determinístico para teste, não criptografia
    for _ in range(1000):
        total = rng.randint(1, MAX_AMOUNT_CENTS)
        ids = rng.sample(range(1, 1000), rng.randint(1, 50))
        parts = split_equal(total, ids)
        ctx = f"total={total} ids={ids}"
        assert list(parts) == ids, ctx
        assert sum(parts.values()) == total, ctx
        assert max(parts.values()) - min(parts.values()) <= 1, ctx
        assert split_equal(total, ids) == parts, ctx
