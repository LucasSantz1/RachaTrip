# Entradas para o Marco 2

Checklist que o plano do Marco 2 (e dos marcos seguintes, quando indicado) deve absorver.

- [ ] **Confiança no proxy e throttling**
  - O Django enxerga o servidor do Next como `REMOTE_ADDR`; o Next repassa sem alterar um `X-Forwarded-For` enviado pelo cliente; o DRF com `NUM_PROXIES=None` confia no cabeçalho inteiro.
  - Antes de ligar o throttling: definir a cadeia confiável (LB, Next, Django), fazer a borda sobrescrever o XFF, ajustar `NUM_PROXIES` a ela e testar que um XFF forjado não muda a identidade do throttle.
- [ ] **Ordem da divisão:** um único helper `shares_for(expense)` = `split_equal(expense.amount_cents, sorted(participant_ids))`, usado por todos os endpoints. Não depender só de `Meta.ordering`.
- [ ] **Campo de valor estrito:** o `IntegerField` do DRF aceita `"1234"` e `12.0`. Usar um campo próprio que rode `validate_amount_cents` sobre o valor JSON cru.
- [ ] **Invariante de mesma viagem:** implementar em `Expense.clean()` / `ExpenseShare.clean()`, reaproveitado pelo serializer e pelo admin. Uma linha cruzando viagens faria o resumo daquela viagem retornar 500 e, por causa do RESTRICT, bloquearia a exclusão da outra viagem.
- [ ] **Admin**
  - Caminho do admin vindo de variável de ambiente, desligado quando ausente.
  - `raw_id_fields`/`autocomplete_fields` e `list_select_related`.
  - Ação de admin para rotacionar tokens: é o caminho de recuperação de um link de admin perdido.
- [ ] **Tokens:** manter `secrets.token_urlsafe(32)`, não `token_hex`. Assim o CHECK de 64 hex minúsculos rejeita qualquer token cru gravado por engano.
- [ ] **Limite de participantes (50):** `select_for_update()` na Trip dentro de `atomic()` antes de contar.
- [ ] **Erros:** `handler404`/`handler500` em JSON com `{code, message}`.
- [ ] **Testes:** um teste de que toda rota nega por padrão, mais os cenários de viagem cruzada e de token antigo após rotação da spec §9.
- [ ] **Marco 4:** `API_INTERNAL_URL` é fixada no `next build`; o build de produção deve falhar quando ela não estiver definida, em vez de cair em `127.0.0.1:8000`.
- [ ] **Marco 3:** decidir sobre `cacheComponents`/`partialPrefetching` e revisar `skipTrailingSlashRedirect` para rotas de página.
