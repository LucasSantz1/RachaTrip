# RachaTrip

App web mobile-first para dividir as despesas de uma viagem em grupo: cada pessoa registra o que pagou e o app calcula quem deve quanto a quem. Backend em Django + DRF + MySQL, frontend em Next.js.

## Pré-requisitos

- Docker Desktop
- Node.js 24 e Python 3.13 (somente para rodar fora do Docker)

## Como rodar

1. Crie o `.env` a partir do exemplo e edite os segredos:

   ```bash
   cp .env.example .env
   ```

   No PowerShell do Windows: `Copy-Item .env.example .env`.

   `DJANGO_SECRET_KEY` precisa ter pelo menos 50 caracteres. Para gerar uma:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

2. Suba os serviços, aplique as migrações e, se quiser, crie um superusuário:

   ```bash
   docker compose up -d --build --wait
   docker compose exec api python manage.py migrate
   docker compose exec api python manage.py createsuperuser
   ```

Endereços:

- Frontend: http://127.0.0.1:3000
- API, pelo frontend: http://127.0.0.1:3000/api/
- Admin do Django: http://127.0.0.1:8000/admin/

Observações:

- `docker/mysql/init.sql` só roda quando o volume `db` é criado pela primeira vez e assume banco e usuário `rachatrip`. Para mudá-los no `.env`, edite o `init.sql` e rode `docker compose down -v`.
- Depois de alterar o `package-lock.json`, use `docker compose up --build --renew-anon-volumes`, pois o volume de `node_modules` fica desatualizado.

## Testes

Suíte completa (backend, com MySQL):

```bash
docker compose exec api pytest
```

Somente o ledger, sem Docker (no Linux/macOS use `.venv/bin` no lugar de `.venv/Scripts`):

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install pytest
.venv/Scripts/python -m pytest -p no:django trips/tests/test_ledger.py
```

Simular uma viagem à mão (usa só o ledger, sem Docker; edite as despesas no arquivo):

```bash
cd backend
.venv/Scripts/python simular_viagem.py
```

Frontend:

```bash
cd frontend
npm ci && npm run lint && npm run build
```

## Documentação

Especificação: [docs/superpowers/specs/2026-11-10-rachatrip-design.md](docs/superpowers/specs/2026-11-10-rachatrip-design.md)
