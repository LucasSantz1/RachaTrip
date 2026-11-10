"""Regras puras de dinheiro do RachaTrip.

Valores monetários são sempre ``int`` em centavos. Este módulo não importa
Django: deve ser testável sem banco nem framework.
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import NamedTuple

MAX_AMOUNT_CENTS = 100_000_000


class LedgerError(ValueError):
    """Erro de regra do ledger. ``code`` identifica o erro de forma estável."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_amount_cents(value: object) -> int:
    """Valida um valor em centavos e o devolve.

    Rejeita qualquer coisa que não seja ``int`` exato (inclui ``bool``, floats,
    strings e ``Decimal``) e valores fora de ``1..MAX_AMOUNT_CENTS``.
    """
    if type(value) is not int:
        raise LedgerError(
            "amount_not_integer",
            f"O valor deve ser um inteiro em centavos, recebido {type(value).__name__}.",
        )
    if not 1 <= value <= MAX_AMOUNT_CENTS:
        raise LedgerError(
            "amount_out_of_range",
            f"O valor deve estar entre 1 e {MAX_AMOUNT_CENTS} centavos, recebido {value}.",
        )
    return value


def split_equal(total_cents: int, participant_ids: Sequence[int]) -> dict[int, int]:
    """Divide ``total_cents`` igualmente entre os participantes, em centavos.

    Cada participante recebe ``total // n``; os primeiros ``total % n`` da
    sequência recebem 1 centavo a mais. O dict segue a ordem de ``participant_ids``.
    """
    validate_amount_cents(total_cents)
    ids = list(participant_ids)
    if not ids:
        raise LedgerError("split_empty", "É preciso ao menos um participante.")
    if len(set(ids)) != len(ids):
        raise LedgerError("split_duplicate", "Participantes repetidos na divisão.")
    base, extra = divmod(total_cents, len(ids))
    return {pid: base + (1 if i < extra else 0) for i, pid in enumerate(ids)}


class ExpenseInput(NamedTuple):
    """Despesa já dividida: quem pagou, o valor e as partes de cada participante."""

    payer_id: int
    amount_cents: int
    shares: Mapping[int, int]


class Balance(NamedTuple):
    """Saldo de um participante: ``net == paid - consumed``."""

    paid: int
    consumed: int
    net: int


def compute_balances(
    participant_ids: Sequence[int], expenses: Iterable[ExpenseInput]
) -> dict[int, Balance]:
    """Calcula pago, consumido e saldo líquido de cada participante.

    Não sabe como a despesa foi dividida: recebe ``shares`` prontas. Cada despesa
    é validada por inteiro antes de acumular, então uma despesa inválida não
    deixa estado parcial. O dict segue a ordem de ``participant_ids``.
    """
    known = set(participant_ids)
    paid = dict.fromkeys(participant_ids, 0)
    consumed = dict.fromkeys(participant_ids, 0)
    for expense in expenses:
        validate_amount_cents(expense.amount_cents)
        if expense.payer_id not in known:
            raise LedgerError("unknown_participant", f"Pagador desconhecido: {expense.payer_id}.")
        if not expense.shares:
            raise LedgerError("shares_empty", "A despesa precisa de ao menos uma parte.")
        for pid, share in expense.shares.items():
            if pid not in known:
                raise LedgerError("unknown_participant", f"Participante desconhecido: {pid}.")
            if share < 0:
                raise LedgerError(
                    "share_negative", f"A parte do participante {pid} não pode ser negativa."
                )
        if sum(expense.shares.values()) != expense.amount_cents:
            raise LedgerError(
                "shares_sum_mismatch",
                "A soma das partes deve ser igual ao valor da despesa.",
            )
        paid[expense.payer_id] += expense.amount_cents
        for pid, share in expense.shares.items():
            consumed[pid] += share
    return {pid: Balance(paid[pid], consumed[pid], paid[pid] - consumed[pid]) for pid in paid}
