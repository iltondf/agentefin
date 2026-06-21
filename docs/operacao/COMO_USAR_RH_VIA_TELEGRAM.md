# Como usar RH via Telegram

> Requer LLM ligada (parser) para frases livres, e escrita habilitada para gravar.
> Sem isso, use as buscas e o fluxo de pendências.

## Exemplos de frases
- "Vanderli fez duas diárias de R$ 120 no pagamento."
- "Vanderli fez duas diárias de R$ 120."  → o bot pergunta: vale ou pagamento?
- "Lança um vale de R$ 200 para o João."
- "Adiciona R$ 150 para o Edson no pagamento."

## Fluxo esperado
1. O bot interpreta (funcionário, tipo, destino, qtd, valor, data).
2. Resolve o funcionário via `buscar_funcionarios` (se houver mais de um, pergunta qual).
3. Usa defaults quando seguro (obra padrão, destino padrão) e **mostra no resumo**.
4. Mostra o resumo e pede **confirmação**.
5. `confirmar N` → grava via `POST /rh/lancamentos` (se escrita habilitada).

## Campos
`funcionarioId` (resolvido por busca), `tipo` (falta|diaria_extra|tarefa|inss_informado|
adiantamento|ajuste_positivo|ajuste_negativo), `destino` (vale|pagamento), `data`, `qtd`,
`valorUnit`, `obraId` (default), `observacao`.

## Debug
`/buscar_funcionario <nome>` lista candidatos com id/cargo.
