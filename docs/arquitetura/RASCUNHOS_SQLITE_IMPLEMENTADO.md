# Rascunhos SQLite — IMPLEMENTADO

## Arquivo
`financebot/drafts.py` — `DraftStore`, `Draft`. Banco: `DATA_DIR/agentefin.db` (volume `/app/data`).

## Tabela `fin_draft`
`id, chat_id, user_id, texto_original, dominio (rh|financeiro|terceirizado|indefinido),
intent, payload_extraido(JSON), campos_faltando(JSON), status, criado_em, atualizado_em,
expires_at, idempotency_key, resultado_api(JSON), erro_api`.
Índice `(user_id, status)`. **Nunca** guarda segredo/chave.

## Estados
`pendente` (faltam campos) · `aguardando_confirmacao` (completo) · `confirmado` (humano OK) ·
`executado` (POST feito) · `erro` · `cancelado`. `expire_old()` cancela vencidos (TTL 48h).

## API
`create(...)`, `get(id)`, `list_active(user_id)`, `update(id, **campos)`, `set_status(id, s)`,
`expire_old()`. `DraftStore.available=False` se não houver persistência → o bot avisa o usuário.

## Comandos (Telegram)
`/pendencias` (ou "pendências"), `detalhar N`, `confirmar N`, `cancelar N`. A confirmação marca
`confirmado`; a **execução** (POST) é gated por WRITE_ENABLED + chave de escrita.

## Persistência
`docker-compose.yml` monta `./data:/app/data`. Sem volume → rascunhos não sobrevivem a redeploy
(o bot degrada e avisa). Logs continuam em stdout.
