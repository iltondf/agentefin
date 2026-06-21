# Como usar o bot por linguagem natural (LLM)

Com `LLM_ENABLED=true`, fale com o bot como com uma secretária — sem comando técnico.

## Ativar (no `.env` da VPS, via operador opção 2)
```
LLM_ENABLED=true
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=<sua chave>     # segredo — nunca versionar
LLM_MODEL=                          # vazio = usa openai/gpt-4o-mini (fallback)
```
Confirme no log (opção 5): `bot_start ... llm=True write=True drafts=True allowed=1`.

## Como falar (exemplos)
**RH:**
- "Vanderli fez duas diárias de R$ 120 no pagamento."
- "Coloca R$ 200 de vale para o Edson."
- "Lança R$ 150 para o João no pagamento."

**Conta a pagar (pendente):**
- "Lança uma conta de R$ 500 da Condor para amanhã."

**Conta paga / compra:**
- "Comprei areia no fornecedor Condor, paguei R$ 1.800 no Pix."
- "Paguei R$ 35 de ferramenta hoje."  (se faltar fornecedor, o bot pergunta)

## Fluxo
1. Você manda a frase → a LLM interpreta (intent + campos).
2. O bot resolve nomes→IDs (busca na API) e aplica **defaults** (mostra "Usei obra padrão: 4").
3. Mostra um **resumo** e pede confirmação.
4. Você responde **"confirmar"** (ou "sim", "ok") → o bot grava (POST) e devolve o ID.
   - **"cancelar"** (ou "não") descarta o rascunho (não grava nada).
5. Se faltar algo essencial (ex.: fornecedor numa compra), o bot pergunta só isso.

## Confirmação/cancelamento natural
- Com **um** rascunho aberto: "confirmar"/"sim"/"ok" confirma; "cancelar"/"não" cancela.
- Com **vários**: o bot pede o número (ex.: `confirmar 3`).

## Pendências
"pendências" (ou "o que está pendente?", "resumo do dia") lista os rascunhos.
`detalhar N`, `confirmar N`, `cancelar N`, `corrigir N <campo> <valor>` continuam disponíveis.

## Fallback técnico (sem LLM)
Se a LLM estiver desligada/instável, os comandos manuais funcionam:
`/rh_teste`, `/cp_teste`, `/conta_paga_teste` (ver `COMO_USAR_*`).

## Segurança
A LLM só **interpreta** (gera JSON) — nunca grava, nunca recebe a chave da API financeira,
nunca inventa IDs. Toda escrita exige confirmação humana + Idempotency-Key. Se a LLM falhar,
o bot responde erro amigável e **não grava**.
