# Evidências — LLM + linguagem natural no Telegram

Data: 2026-06-21.

## Configuração
- Modelo escolhido: **`deepseek/deepseek-v4-flash`** (fallbacks: `qwen/qwen3.5-flash-02-23`,
  `google/gemini-2.5-flash-lite`). Se `LLM_MODEL` vazio → `openai/gpt-4o-mini`.
- Provider: openrouter; chave via `OPENROUTER_API_KEY` (segredo, não versionado).
- **Modo conversacional:** parser devolve `reply`/`calculos`/`intent` (inclui `conversa`).
  Conversa e cálculo **não** criam rascunho; só intenção de lançar + confirmação grava.
- Defaults (`defaults.yaml`): obra **4**, conta **5**, forma **pix**, categorias areia/material/
  ferramenta/… → **15**, `rh.destinoPadrao=pagamento`.

## O que foi validado (código + testes)
- **64 testes** (pytest) incluindo: parser monta request correto (modelo fallback, Bearer
  OPENROUTER, `response_format=json_object`) e parseia o JSON; confirmação/cancelamento natural
  (sem número) agindo no único rascunho; `categoriaPalavra`+defaults na resolução; gating de escrita.
- **Fluxo natural** ligado no router: qualquer texto livre (não-comando, não-pendência) →
  `parser.parse` → rascunho → resolve (IDs+defaults) → **resumo** → confirmar/cancelar natural.
- Pipeline de escrita já validado em produção (POSTs reais #291/#929/#930, idempotência).

> A chamada **LLM ao vivo** depende da `OPENROUTER_API_KEY` (configurada na VPS, não nesta
> máquina de dev). Validação ao vivo = etapa no Telegram (abaixo).

## Testes a fazer no Telegram (VPS, após `llm=True`)
| Frase | Esperado |
|---|---|
| `[TESTE_AGENT_READY] Edson fez uma diária de R$ 1 no pagamento hoje` | resumo RH → "confirmar" → lançamento criado |
| `[TESTE_AGENT_READY] Edson fez uma diária de R$ 1 hoje` | usa destino padrão "pagamento" (mostra no resumo) |
| `[TESTE_AGENT_READY] lança uma conta de R$ 1 para Condor para amanhã` | conta pendente, categoria 15/obra 4 default → confirmar |
| `[TESTE_AGENT_READY] comprei ferramenta de R$ 1 no fornecedor Condor e paguei no Pix hoje` | conta paga (conta 5, pix) → confirmar |
| `[TESTE_AGENT_READY] comprei uma ferramenta de R$ 1 hoje` | pergunta "Qual foi o fornecedor?" |
| `pendências` | lista rascunhos |
| `confirmar` / `cancelar` | age no único rascunho aberto |

## Resultado ao vivo (preencher após teste no Telegram)
- llm no log: `bot_start ... llm=True write=True drafts=True allowed=1` — *(confirmar)*
- frases testadas / respostas / IDs criados — *(preencher; usar [TESTE_AGENT_READY], R$ 1)*
- confirmação natural OK? cancelamento natural OK? defaults aplicados? — *(preencher)*

## Segurança
Chave OpenRouter e write nunca logadas/versionadas. **Rotacionar** chaves expostas no chat.
