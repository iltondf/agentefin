# Como usar Contas a Pagar / Compras via Telegram

> Requer LLM ligada (parser) para frases livres, e escrita habilitada para gravar.

## Exemplos de frases
- "Lança uma conta de R$ 500 da Condor para amanhã."  → conta a pagar pendente.
- "Comprei areia no fornecedor Areião, R$ 1.800 no Pix."  → conta a pagar **já paga**.
- "Paguei R$ 35 de ferramenta hoje."

## Fluxo — conta pendente
1. Resolve fornecedor (`buscar_fornecedores`; se ambíguo, pergunta).
2. Categoria por palavra (default) e obra padrão (mostra no resumo). Mão de Obra exige obra.
3. Resumo + **confirmação** → `POST /financeiro/contas-pagar` (`pago:false`).

## Fluxo — conta já paga
1. Resolve fornecedor + conta bancária (default) + forma (pix por padrão) + data (hoje).
2. Resumo + **confirmação** → `POST /financeiro/contas-pagar` (`pago:true`) → cria CP + baixa.
3. Faltando conta/forma → o bot pergunta (`FALTA_CONTA_ORIGEM`/`FALTA_FORMA_PAGAMENTO`).

## Debug
`/buscar_fornecedor <nome>` · `/buscar_conta <nome>` · `/buscar_contas_pagar` (via tool).

## Regras de preenchimento automático (defaults)
- **Obra:** sem informar → usa a obra padrão (4). Mostra "Usei obra padrão: 4".
- **Categoria:** informe se quiser ("categoria X"); senão tenta pela palavra (areia/ferramenta→15);
  senão usa a **categoria padrão (15)**. **Nunca pergunta** a categoria.
- **Forma de pagamento:** se você disser "no Pix/dinheiro/transferência/cartão", usa isso; senão **assume Pix**.
- **Conta de saída:** se não disser, usa a **conta padrão (final 85)**. Você pode dizer
  "conta 1"/"conta um"/"final 85" → conta final 85; "conta 2"/"conta dois"/"final 97" → conta final 97.
  Conta não reconhecida → o bot pergunta qual.
- **Pago × a vencer:** "comprei/paguei" → conta **paga** (hoje); "a vencer em [data]" / "lança uma conta…
  para [data]" → conta **pendente**.
- **Fornecedor:** resolve pelo nome. Se houver **vários parecidos**, o bot **pergunta qual**. Se **não
  achar nenhum**, lança em **"Outros"** e marca `[AJUSTAR FORNECEDOR: <nome>]` na observação para você
  acertar/cadastrar depois no sistema web (requer `fornecedorOutrosId` no `defaults.yaml`).

## Comandos manuais (sem LLM)
- `/cp_teste <fornecedor> <valor> [amanha]` → conta pendente (rascunho → `confirmar N`).
- `/conta_paga_teste <fornecedor> <valor> [pix] [hoje]` → conta paga.
> Categoria/obra/conta vêm de `defaults.yaml` quando configurados; senão o bot pergunta.

## Importante
Nada é gravado sem **confirmação** (`confirmar N`). Duplicado provável → o bot avisa.

## Validado (2026-06-21)
`POST /financeiro/contas-pagar` → **#929** (pendente) e **#930** (paga, Pix/CEF), R$ 1,00 cada,
`[TESTE_AGENT_READY]`; replay idempotente não duplica; conflito de key → 409 tratado.
