# RachaTrip

App web mobile-first para dividir as despesas de uma viagem em grupo: cada pessoa registra o que pagou e o app calcula quem deve quanto a quem. Backend em Django + DRF + MySQL, frontend em Next.js.

## Pré-requisitos

- Docker Desktop
- Python 3.13+ e Node.js (somente para rodar fora do Docker)

## Como rodar

```bash
cp .env.example .env   # ajuste os valores
docker compose up
```

## Testes

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install pytest ruff   # Windows; no Linux/macOS use .venv/bin
.venv/Scripts/python -m pytest -p no:django
.venv/Scripts/ruff check .
```

## Documentação

Especificação: [docs/superpowers/specs/2026-11-10-rachatrip-design.md](docs/superpowers/specs/2026-11-10-rachatrip-design.md)
