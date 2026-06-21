# Rascunhos / Pendências — design (planejamento, NÃO implementado)

Captura rápida durante o dia → confirmação depois → POST só na confirmação.

## Onde armazenar (decisão)
| Opção | Simplicidade | Persistência | Recom. |
|---|---|---|---|
| A) **SQLite local no agente** (volume `/app/data`) | alta | sim (se houver volume) | ✅ **escolhido** |
| B) Arquivo JSON local | alta | frágil (concorrência) | não |
| C) Tabela no BRGlobal | média | sim | ❌ não há endpoint de inbox; exigiria mudar o financeiro |
| D) Não armazenar (confirmar na hora) | máxima | — | só fallback se faltar volume |

**Recomendação: SQLite local em volume persistente.** Hoje o `docker-compose.yml` é **stateless
(sem volumes)** → **Fase 2 exige adicionar volume `/app/data`** (mudança pequena, documentada).
Sem volume → degradar para modo D (confirmar imediatamente) e **avisar** o usuário.

## Esquema do rascunho (`fin_draft`)
```
id INTEGER PK
chat_id, user_id           # Telegram (autoria/escopo)
texto_original             # frase literal
dominio                    # rh | financeiro | terceirizado | indefinido
intent                     # ex.: criar_lancamento_rh
payload_extraido (JSON)    # campos já resolvidos (IDs vindos das buscas)
campos_faltando (JSON)     # lista do que falta perguntar
status                     # pendente | aguardando_confirmacao | confirmado | cancelado | executado | erro
criado_em, atualizado_em, expires_at
idempotency_key            # gerada na CONFIRMAÇÃO (estável no retry)
resultado_api (JSON), erro_api (texto)
```
Índices: `(user_id,status)`, `expires_at`. **Sem segredo** no rascunho (nunca a chave).

## Comandos / mensagens
`pendências` / `listar pendências` · `confirmar tudo` · `confirmar N` · `cancelar N` ·
`corrigir N <campo> <valor>` · `detalhar N` · `resumo do dia`.

## Ciclo de vida
`pendente` (faltam campos) → pergunta → `aguardando_confirmacao` (completo, resumo mostrado) →
usuário confirma → `confirmado` → POST → `executado` (guarda `resultado_api`) **ou** `erro`
(guarda `erro_api`, permite corrigir/retry). `expires_at` (ex.: 24–48h) → `cancelado` automático.

## Regras
- Rascunho **pode existir sem escrever** no BRGlobal. **POST só após confirmação.**
- IDs no `payload_extraido` vêm de **tools de busca** (nunca inventados pela LLM).
- Confirmar item já `executado` → não repete (idempotência + status).
- `idempotency_key` é **gerada na confirmação** e reusada em retry (não muda).

## Riscos e mitigação
| Risco | Mitigação |
|---|---|
| Container sem volume perde rascunho | Fase 2 adiciona volume; se ausente, modo D + aviso |
| Duplicidade | `Idempotency-Key` (servidor) + status `executado` + guard `DUPLICADO_PROVAVEL` |
| Confirmar item errado | resumo numerado + `detalhar N` antes; `confirmar N` explícito |
| Rascunho antigo | `expires_at` → cancelamento automático |
| Estado mudou no BRGlobal entre captura e confirmação | re-resolver IDs/validar no momento da confirmação; servidor é a verdade |
