import random
from decimal import Decimal

import pytest

from trips.ledger import (
    MAX_AMOUNT_CENTS,
    Balance,
    ExpenseInput,
    LedgerError,
    Transfer,
    compute_balances,
    split_equal,
    suggest_settlements,
    validate_amount_cents,
)


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
    assert "recebido" not in str(e.value)
    if value != 0:
        assert str(value) not in str(e.value)


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
    seed = 20261110
    rng = random.Random(seed)
    for _ in range(1000):
        total = rng.randint(1, MAX_AMOUNT_CENTS)
        ids = rng.sample(range(1, 1000), rng.randint(1, 50))
        parts = split_equal(total, ids)
        ctx = f"seed={seed} total={total} ids={ids}"
        assert list(parts) == ids, ctx
        assert sum(parts.values()) == total, ctx
        assert max(parts.values()) - min(parts.values()) <= 1, ctx
        assert split_equal(total, ids) == parts, ctx


def test_balances_no_expenses():
    assert compute_balances([1, 2], []) == {1: Balance(0, 0, 0), 2: Balance(0, 0, 0)}


def test_balances_partial_split():
    expense = ExpenseInput(1, 9000, split_equal(9000, [1, 2]))
    result = compute_balances([1, 2, 3], [expense])
    assert result == {
        1: Balance(9000, 4500, 4500),
        2: Balance(0, 4500, -4500),
        3: Balance(0, 0, 0),
    }
    assert list(result) == [1, 2, 3]


def test_balances_payer_outside_split():
    result = compute_balances([1, 2, 3], [ExpenseInput(1, 3000, split_equal(3000, [2, 3]))])
    assert result[1].net == 3000


def test_balances_unequal_shares():
    result = compute_balances([1, 2], [ExpenseInput(1, 1000, {1: 700, 2: 300})])
    assert result[1].net == 300
    assert result[2].net == -300


@pytest.mark.parametrize(
    ("expense", "code"),
    [
        (ExpenseInput(9, 1000, {1: 1000}), "unknown_participant"),
        (ExpenseInput(1, 1000, {1: 500, 9: 500}), "unknown_participant"),
        (ExpenseInput(1, 1000, {1: 600, 2: 300}), "shares_sum_mismatch"),
        (ExpenseInput(1, 1000, {1: 1500, 2: -500}), "share_negative"),
        (ExpenseInput(1, 1000, {}), "shares_empty"),
        (ExpenseInput(1, 0, {1: 0}), "amount_out_of_range"),
    ],
)
def test_balances_errors(expense, code):
    with pytest.raises(LedgerError) as e:
        compute_balances([1, 2], [expense])
    assert e.value.code == code


def test_balances_invalid_expense_after_valid_raises():
    good = ExpenseInput(1, 1000, {1: 1000})
    bad = ExpenseInput(1, 1000, {1: 1})
    with pytest.raises(LedgerError):
        compute_balances([1, 2], [good, bad])


def test_balances_properties_random():
    seed = 20261111
    rng = random.Random(seed)
    for case in range(1000):
        ids = rng.sample(range(1, 1000), rng.randint(2, 20))
        expenses = []
        for _ in range(rng.randint(0, 30)):
            amount = rng.randint(1, 10_000_000)
            subset = rng.sample(ids, rng.randint(1, len(ids)))
            expenses.append(ExpenseInput(rng.choice(ids), amount, split_equal(amount, subset)))
        total = sum(x.amount_cents for x in expenses)
        result = compute_balances(ids, expenses)
        ctx = f"seed={seed} case={case} ids={ids} expenses={expenses}"
        assert list(result) == ids, ctx
        assert sum(b.net for b in result.values()) == 0, ctx
        assert sum(b.paid for b in result.values()) == total, ctx
        assert sum(b.consumed for b in result.values()) == total, ctx
        assert all(b.net == b.paid - b.consumed for b in result.values()), ctx


@pytest.mark.parametrize(
    "shares",
    [
        {1: 500.0, 2: 500.0},
        {1: True, 2: 999},
        {1: Decimal("500"), 2: Decimal("500")},
    ],
)
def test_balances_rejects_non_int_share(shares):
    with pytest.raises(LedgerError) as e:
        compute_balances([1, 2], [ExpenseInput(1, 1000, shares)])
    assert e.value.code == "share_not_integer"


def _bal(net):
    return Balance(paid=0, consumed=0, net=net)


def test_settlements_all_even():
    assert suggest_settlements({1: _bal(0), 2: _bal(0)}) == []


def test_settlements_greedy_largest_debtor_first():
    balances = {1: _bal(3000), 2: _bal(-1000), 3: _bal(-2000)}
    assert suggest_settlements(balances) == [Transfer(3, 1, 2000), Transfer(2, 1, 1000)]


def test_settlements_tie_break_by_registration_order():
    balances = {1: _bal(500), 2: _bal(500), 3: _bal(-1000)}
    assert suggest_settlements(balances) == [Transfer(3, 1, 500), Transfer(3, 2, 500)]


def test_settlements_tie_break_debtors_by_registration_order():
    balances = {
        1: Balance(0, 500, -500),
        2: Balance(0, 500, -500),
        3: Balance(1000, 0, 1000),
    }
    assert suggest_settlements(balances) == [Transfer(1, 3, 500), Transfer(2, 3, 500)]


def test_settlements_sole_payer_owes_nothing():
    balances = compute_balances([1], [ExpenseInput(1, 1000, {1: 1000})])
    assert suggest_settlements(balances) == []


def test_settlements_zero_share_participant_not_involved():
    shares = split_equal(1, [1, 2, 3])
    balances = compute_balances([1, 2, 3], [ExpenseInput(1, 1, shares)])
    zero_share = [pid for pid, s in shares.items() if s == 0]
    assert zero_share
    result = suggest_settlements(balances)
    for t in result:
        assert t.from_id not in zero_share and t.to_id not in zero_share


def test_settlements_rejects_non_zero_sum():
    with pytest.raises(LedgerError) as e:
        suggest_settlements({1: _bal(100), 2: _bal(-50)})
    assert e.value.code == "balances_not_zero_sum"


def test_settlements_random_invariants():
    seed = 20261112
    rng = random.Random(seed)
    for case in range(1000):
        ids = rng.sample(range(1, 1000), rng.randint(2, 20))
        expenses = []
        for _ in range(rng.randint(0, 30)):
            amount = rng.randint(1, 10_000_000)
            subset = rng.sample(ids, rng.randint(1, len(ids)))
            expenses.append(ExpenseInput(rng.choice(ids), amount, split_equal(amount, subset)))
        balances = compute_balances(ids, expenses)
        result = suggest_settlements(balances)
        ctx = f"seed={seed} case={case} ids={ids} expenses={expenses} result={result}"
        remaining = {pid: b.net for pid, b in balances.items()}
        for t in result:
            remaining[t.from_id] += t.amount_cents
            remaining[t.to_id] -= t.amount_cents
        assert all(v == 0 for v in remaining.values()), ctx
        assert len(result) <= len(ids) - 1, ctx
        assert all(t.amount_cents > 0 for t in result), ctx
        assert all(t.from_id != t.to_id for t in result), ctx
        assert suggest_settlements(balances) == result, ctx
