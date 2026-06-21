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

## Importante
Nada é gravado sem **confirmação**. Duplicado provável → o bot avisa e só grava se você confirmar.
