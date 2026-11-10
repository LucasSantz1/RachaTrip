from decimal import Decimal

import pytest

from trips.ledger import MAX_AMOUNT_CENTS, LedgerError, validate_amount_cents


@pytest.mark.parametrize("value", [1, 1234, MAX_AMOUNT_CENTS])
def test_accepts_valid_cents(value):
    assert validate_amount_cents(value) == value


@pytest.mark.parametrize("value", [True, False, 12.0, 12.5, "1234", None, Decimal("12")])
def test_rejects_non_int(value):
    with pytest.raises(LedgerError) as e:
        validate_amount_cents(value)
    assert e.value.code == "amount_not_integer"


@pytest.mark.parametrize("value", [0, -1, MAX_AMOUNT_CENTS + 1])
def test_rejects_out_of_range(value):
    with pytest.raises(LedgerError) as e:
        validate_amount_cents(value)
    assert e.value.code == "amount_out_of_range"
