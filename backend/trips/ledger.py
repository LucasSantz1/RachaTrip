"""Regras puras de dinheiro do RachaTrip.

Valores monetários são sempre ``int`` em centavos. Este módulo não importa
Django: deve ser testável sem banco nem framework.
"""

from collections.abc import Sequence

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
