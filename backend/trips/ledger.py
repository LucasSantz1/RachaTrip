"""Regras puras de dinheiro do RachaTrip.

Valores monetários são sempre ``int`` em centavos. Este módulo não importa
Django: deve ser testável sem banco nem framework.
"""

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
            f"O valor deve ser um inteiro em centavos, recebido {value!r}.",
        )
    if not 1 <= value <= MAX_AMOUNT_CENTS:
        raise LedgerError(
            "amount_out_of_range",
            f"O valor deve estar entre 1 e {MAX_AMOUNT_CENTS} centavos, recebido {value}.",
        )
    return value
