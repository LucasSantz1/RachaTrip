"""Simula uma viagem com as regras de dinheiro do RachaTrip (sem Django nem banco).

Uso, dentro de backend/:  python simular_viagem.py
Edite PESSOAS e DESPESAS para testar outros cenários. Valores em centavos.
"""

from trips.ledger import ExpenseInput, compute_balances, split_equal, suggest_settlements

PESSOAS = {1: "Ana", 2: "Bruno", 3: "Carla", 4: "Davi", 5: "Eva"}
TODOS = list(PESSOAS)

# (quem pagou, valor em centavos, entre quem dividir, descrição)
DESPESAS = [
    (1, 30000, TODOS, "Combustível"),
    (2, 100000, TODOS, "Hospedagem"),
    (3, 25000, [1, 2, 3], "Mercado (só Ana, Bruno e Carla)"),
]


def reais(centavos: int) -> str:
    return f"R$ {centavos / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


entradas = [
    ExpenseInput(pagou, valor, split_equal(valor, entre)) for pagou, valor, entre, _ in DESPESAS
]
saldos = compute_balances(TODOS, entradas)

print("Saldos:")
for pid, b in saldos.items():
    print(
        f"  {PESSOAS[pid]:<6} pagou {reais(b.paid):>12}"
        f"  consumiu {reais(b.consumed):>12}  saldo {reais(b.net):>12}"
    )

print("\nAcertos sugeridos:")
for t in suggest_settlements(saldos):
    print(f"  {PESSOAS[t.from_id]} paga {reais(t.amount_cents)} para {PESSOAS[t.to_id]}")
