# RachaTrip — Especificação de design (MVP)

Data: 2026-11-10 · Status: aguardando revisão

## 1. Objetivo

App web mobile-first para organizar despesas de viagens em grupo: registrar quem pagou cada conta, com quem ela é dividida, calcular saldos e sugerir transferências para quitar tudo.

Sucesso no MVP: um grupo cria uma viagem, lança despesas pelo celular e, ao final, vê quanto cada pessoa deve e uma lista curta de transferências que zera todos os saldos — sem erro de um centavo.

### Dentro do escopo
- Viagem: nome, destino, período, participantes.
- Acesso por dois links secretos (admin e grupo), sem contas de usuário.
- Despesas: descrição, valor, categoria, data, quem pagou, entre quem dividir (divisão igualitária entre os selecionados).
- Saldos por participante (pago, consumido, saldo líquido).
- Sugestão de transferências.

### Fora do escopo (exige revisão de escopo para entrar)
- Contas de usuário, login, recuperação de senha.
- Integração bancária, Pix, pagamentos.
- IA de qualquer tipo.
- Divisão por valores ou pesos diferentes (só igualitária no MVP; o caminho para adicioná-la está em 4.5).
- Registrar que uma transferência sugerida foi paga.
- Múltiplas moedas (só BRL).

## 2. Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js (App Router) + React + TypeScript (strict) |
| Estilo | Tailwind CSS + shadcn/ui |
| Backend | Python + Django + Django REST Framework |
| Banco | MySQL 8 (`utf8mb4`, modo estrito) via Django ORM |
| Testes | pytest + pytest-django |
| Lint | ruff (backend), ESLint (frontend) |
| Ambiente | Docker + Docker Compose |
| CI | GitHub Actions |

Versões estáveis exatas são fixadas no Marco 0. Nenhuma dependência além desta tabela sem justificativa.

Django Auth é usado apenas para o `/admin` interno. Usuários finais não têm conta.

## 3. Estrutura do repositório

```
RachaTrip/
├── backend/
│   ├── config/          settings lidos de variáveis de ambiente
│   └── trips/
│       ├── ledger.py    regras financeiras puras (sem Django)
│       ├── models.py
│       ├── access.py    geração/verificação de tokens e permissão (Marco 2)
│       └── api/         serializers, views, urls (Marco 2)
├── frontend/
├── docs/
├── docker-compose.yml
├── .env.example
└── .github/workflows/
```

`ledger.py` não importa nada do Django. Isso mantém as regras de dinheiro testáveis em milissegundos e isoladas do resto.

## 4. Regras financeiras (`trips/ledger.py`)

Todo valor monetário é `int` em centavos em todas as camadas: banco, Python, JSON e TypeScript. Nenhum `float` toca dinheiro.

### 4.1 `validate_amount_cents(value) -> int`
- Aceita somente `int` do Python (rejeita `bool`, `float`, `str`, `Decimal`, `None`).
- Intervalo: `1 ≤ value ≤ 100_000_000` (R$ 0,01 a R$ 1.000.000,00).
- Erro: `ValueError` com código estável (`amount_not_integer`, `amount_out_of_range`).
- Usada pela API como validação na fronteira de confiança. A conversão do texto digitado para centavos acontece no frontend (máscara monetária, Marco 3) e nunca é aceita pela API.

### 4.2 `split_equal(total_cents, participant_ids) -> dict[id, int]`
- `participant_ids` é uma sequência ordenada e não vazia, sem repetições.
- Cada um recebe `total // n`; os `total % n` centavos restantes vão, um para cada, aos primeiros da sequência.
- O chamador passa os participantes ordenados por ordem de cadastro (`id`), o que torna o resultado estável.
- Garantias: soma das partes = total; diferença entre partes ≤ 1; mesma entrada → mesma saída.
- Erros: lista vazia, ids repetidos, total inválido.

Exemplos: 10000 / 3 → 3334, 3333, 3333. 1 / 3 → 1, 0, 0.

### 4.3 `compute_balances(participant_ids, expenses) -> dict[id, Balance]`
- `expenses`: sequência de `(payer_id, amount_cents, shares)`, onde `shares` é `dict[id, int]` com a parte de cada participante em centavos.
- `compute_balances` não sabe como a despesa foi dividida: recebe as partes prontas. No MVP elas vêm de `split_equal`; no futuro, de outras funções de divisão (ver 4.5).
- `paid` = soma do que o participante pagou; `consumed` = soma das suas partes; `net = paid − consumed`.
- Garantias: soma de `net` = 0; participante fora da divisão não tem `consumed` afetado; pagador fora da divisão fica credor do valor inteiro.
- Erros: `payer_id` ou alguma chave de `shares` fora de `participant_ids`; soma de `shares` diferente de `amount_cents`; parte negativa; `shares` vazio.

### 4.4 `suggest_settlements(balances) -> list[Transfer]`
- `Transfer = (from_id, to_id, amount_cents)`.
- Guloso: a cada passo, o maior devedor paga ao maior credor o mínimo entre a dívida e o crédito. Empates são desfeitos pela ordem de cadastro.
- Garantias: aplicar as transferências zera todos os saldos; no máximo `n − 1` transferências; nenhuma de valor 0; nenhuma de alguém para si mesmo; mesma entrada → mesma saída; todos quites → lista vazia.
- Não garante o mínimo absoluto de transferências (problema NP-difícil). Aceito.

### 4.5 Evolução prevista: divisão não igualitária (fora do MVP)
Não será construída agora, mas o MVP é desenhado para que ela entre só com acréscimos, sem reescrever saldos, acertos nem dados existentes:
- **Cálculo:** novas funções produzem o mesmo `dict[id, int]` que `split_equal`, por exemplo `split_by_amounts` (valores fixos; a soma tem que bater com o total) e `split_by_weights` (pesos ou porcentagens; centavos restantes distribuídos pelo maior resto, com desempate pela ordem de cadastro). `compute_balances` e `suggest_settlements` não mudam.
- **Banco:** migration só de acréscimo: `Expense.split_mode` (padrão `equal`, então despesas antigas continuam iguais) e `ExpenseShare.share_cents` ou `weight`, preenchido apenas nos modos novos.
- **API:** o corpo da despesa ganha `split_mode` opcional; sem ele, o comportamento é o igualitário de hoje.

## 5. Modelo de dados

Datas em UTC; `DateField` para datas de viagem/despesa.

**Trip**
- `public_id` UUID, único, usado nas URLs. O `id` sequencial nunca sai da API.
- `name` (1–100), `destination` (0–100), `start_date`, `end_date`.
- `admin_token_hash`, `share_token_hash`: 64 caracteres hex (SHA-256), ambos únicos.
- `created_at`.
- Constraint: `end_date ≥ start_date`.

**Participant**
- `trip` → Trip (CASCADE), `name` (1–60), `created_at`.
- Constraint: único `(trip, name)`.
- Limite de 50 participantes por viagem (validado na aplicação).

**Expense**
- `trip` → Trip (CASCADE), `description` (1–120), `amount_cents` (int), `category`, `date`, `payer` → Participant (RESTRICT), `created_at`.
- `category`: `transporte`, `hospedagem`, `alimentacao`, `mercado`, `passeios`, `outros`.
- Constraint: `1 ≤ amount_cents ≤ 100_000_000`.

**ExpenseShare** (com quem a despesa é dividida)
- `expense` → Expense (CASCADE), `participant` → Participant (RESTRICT).
- Constraint: único `(expense, participant)`.
- Guarda só quem participa; o valor de cada parte é calculado na leitura por `split_equal`. Não há soma a manter consistente no banco.

**Regras que o banco não expressa e a aplicação garante (com teste):**
- `payer` e todos os participantes de `ExpenseShare` pertencem à mesma viagem da despesa. Sem isso, um token de uma viagem poderia referenciar participantes de outra.
- Toda despesa tem pelo menos um participante na divisão.

**Exclusões:**
- Excluir a viagem apaga tudo em cascata (RESTRICT permite, pois os objetos que referenciam também estão sendo apagados).
- Excluir um participante que pagou ou participa de alguma despesa falha (API responde 409).

## 6. Acesso por links secretos

- Na criação, o servidor gera dois tokens com `secrets.token_urlsafe(32)` (256 bits): **admin** e **grupo**. O banco guarda só o SHA-256 de cada um. Os tokens puros são devolvidos uma única vez, na resposta da criação.
- Formato do link: `https://<domínio>/v/<public_id>#<token>`. O fragmento (`#`) não é enviado ao servidor pelo navegador, então não aparece em logs nem no Referer.
- O frontend lê o fragmento e envia o token em `X-Trip-Token`. O token fica em `sessionStorage` (não em `localStorage`, não em cookie).
- Verificação: busca a viagem pelo `public_id`, calcula o SHA-256 do token recebido e compara com os dois hashes via `hmac.compare_digest`. O resultado define o papel: `admin`, `member` ou nenhum.
- Viagem inexistente, token ausente ou inválido → **404** idêntico nos três casos.

| Ação | Grupo | Admin |
|---|---|---|
| Ver viagem, participantes, despesas, saldos, acertos | ✓ | ✓ |
| Criar, editar e excluir despesas | ✓ | ✓ |
| Editar viagem; adicionar, renomear e excluir participantes | | ✓ |
| Trocar o link do grupo (o antigo deixa de funcionar na hora) | | ✓ |
| Trocar o próprio link de admin | | ✓ |
| Excluir a viagem | | ✓ |

Ação de admin feita com token de grupo → **403** (o grupo já sabe que a viagem existe).

**Riscos aceitos:** link de admin perdido não tem recuperação (só via `/admin`). A tela de criação pede para salvar o link e oferece botão de copiar. Quem tem o link do grupo pode apagar despesas; a mitigação é o admin trocar o link.

## 7. API (Marco 2, visão geral)

Prefixo `/api/`. JSON. Erros no formato `{"code": "...", "message": "..."}`, sem stack trace.

| Método e rota | Papel |
|---|---|
| `POST /trips/` | público, com limite por IP |
| `GET/PATCH/DELETE /trips/{public_id}/` | GET: grupo; PATCH/DELETE: admin |
| `POST /trips/{public_id}/rotate-share-token/` | admin |
| `POST /trips/{public_id}/rotate-admin-token/` | admin |
| `GET/POST /trips/{public_id}/participants/` | GET: grupo; POST: admin |
| `PATCH/DELETE /trips/{public_id}/participants/{id}/` | admin |
| `GET/POST /trips/{public_id}/expenses/` | grupo |
| `PATCH/DELETE /trips/{public_id}/expenses/{id}/` | grupo |
| `GET /trips/{public_id}/summary/` | grupo: saldos e transferências sugeridas |
| `GET /health/` | público |

Listas paginadas. Recursos filhos sempre filtrados pela viagem do token, nunca só pelo id.

## 8. Segurança (base para todos os marcos)

- Segredos só via variáveis de ambiente; `.env` no `.gitignore`; `.env.example` sem valores reais. Sem `SECRET_KEY`, o app não sobe.
- `DEBUG=False` fora do desenvolvimento; `ALLOWED_HOSTS` explícito.
- Validação estrita na entrada: tamanhos máximos, tipos exatos, campos permitidos explícitos nos serializers (sem `fields = "__all__"`).
- Limite de requisições por IP (throttling do DRF): criação de viagem mais restrita que leitura.
- Headers: `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, HSTS em produção, CSP no frontend (Marco 3).
- Sem scripts de terceiros nas páginas de viagem.
- `X-Trip-Token` nunca é logado.
- MySQL sem porta exposta fora da rede do Docker.

## 9. Testes

- `ledger.py`: testes de exemplo + testes aleatórios com `random` e semente fixa (≥ 1000 casos por regra). Em caso de falha, a semente e a entrada aparecem na mensagem.
- Models: testes provando que o banco rejeita dados inválidos (constraints).
- API (Marco 2): testes de integração, incluindo acesso indevido (token de outra viagem, token de grupo em ação de admin, token antigo após troca, participante de outra viagem numa despesa).
- CI roda tudo contra MySQL real.

## 10. Marcos e tarefas

### Marco 0 — Fundação

| # | Tarefa | Critérios de aceite |
|---|---|---|
| M0-1 | Repositório: `git init`, README, `.gitignore`, `.env.example` | `.env` e chaves estão ignorados; `.env.example` lista todas as variáveis sem valores reais; README explica como subir o projeto. |
| M0-2 | Django + DRF com settings por ambiente | `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` e credenciais do banco vêm do ambiente; sem `SECRET_KEY` o app não sobe; `GET /api/health/` responde 200 e confirma acesso ao banco. |
| M0-3 | Docker Compose: MySQL 8 + api + web | `docker compose up` sobe os três com healthchecks; a api espera o banco; banco em `utf8mb4` e modo estrito; porta do MySQL não exposta. |
| M0-4 | pytest, pytest-django, ruff | `pytest` passa com um teste inicial; `ruff check` passa; testes de `ledger.py` rodam sem banco. |
| M0-5 | Next.js + TS strict + Tailwind + shadcn/ui | `npm run build` e `npm run lint` passam; cores e tipografia definidas como variáveis; página inicial é só placeholder. |
| M0-6 | GitHub Actions | Em cada push: lint e testes do backend contra MySQL, lint e build do frontend; qualquer falha derruba o job. |

### Marco 1 — Núcleo financeiro

| # | Tarefa | Critérios de aceite |
|---|---|---|
| M1-1 | `validate_amount_cents` | Conforme 4.1, com teste para cada tipo rejeitado e para os limites (0, 1, 100_000_000, 100_000_001). |
| M1-2 | `split_equal` | Conforme 4.2, com os exemplos fixos e o teste aleatório das garantias. |
| M1-3 | `compute_balances` | Conforme 4.3, incluindo divisão parcial, pagador fora da divisão e partes desiguais (prova que a função já aceita divisões não igualitárias); rejeita partes cuja soma difere do total; teste aleatório de soma zero. |
| M1-4 | `suggest_settlements` | Conforme 4.4; teste aleatório confirmando saldos zerados e no máximo `n − 1` transferências. |
| M1-5 | Models + migrations + constraints | Conforme seção 5; testes provando cada constraint; exclusão de viagem em cascata funciona; exclusão de participante com despesas falha; nenhum token puro gravado. Migration revisada antes do commit. |

Ordem sugerida: M0-1 → M0-2 → M0-4 → M1-1 → M1-2 → M1-3 → M1-4 → M0-3 → M0-5 → M0-6 → M1-5.

### Marcos seguintes (detalhados quando chegarem)
- **Marco 2 — API e segurança:** endpoints da seção 7, `access.py`, throttling, formato de erro, testes de acesso indevido.
- **Marco 3 — Interface:** pesquisa de referências visuais, criação de viagem, participantes, formulário de despesa com máscara monetária, resumo e acertos, estados de carregamento/vazio/erro, acessibilidade.
- **Marco 4 — Publicação:** deploy separado de frontend e API, HTTPS, banco gerenciado com backup, cache compartilhado para o throttling, documentação e estudo de caso.

## 11. Decisões registradas

- Acesso por links secretos em vez de contas (escolha do usuário em 2026-11-10, após avaliar contas com Django Auth).
- Não criar modelo `User` customizado: não há usuários finais. Se contas entrarem no futuro, a migração de modelo de usuário terá custo extra.
- Testes aleatórios com `random` em vez de Hypothesis: sem dependência nova; perde-se a redução automática do caso de falha.
- Valor das partes calculado na leitura, não armazenado.
