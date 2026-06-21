# Como usar Pendências (rascunhos)

O bot captura pedidos rápidos como **rascunho** e só grava após você confirmar.

## Comandos
- `/pendencias` (ou escreva "pendências") — lista os rascunhos ativos.
- `detalhar N` — mostra todos os campos do rascunho N.
- `confirmar N` — **resolve nomes→IDs, valida e GRAVA** (POST) se a escrita estiver habilitada;
  senão deixa o rascunho confirmado para gravar depois. Reconfirmar item já executado não duplica.
- `cancelar N` — cancela o rascunho N (nenhum POST). **Não apaga nada no BRGlobal.**
- `corrigir N <campo> <valor>` — ajusta um campo do rascunho (ex.: `corrigir 3 valor 2`).

## Criar rascunho sem LLM (comandos manuais)
- `/rh_teste <funcionario> <tipo> <vale|pagamento> <valor> [hoje]`
- `/cp_teste <fornecedor> <valor> [amanha]`
- `/conta_paga_teste <fornecedor> <valor> [pix] [hoje]`
Com LLM ligada, frases naturais também criam rascunho.

## Fluxo
1. Você manda uma frase ("comprei areia R$ 1.800 no Pix").
2. Com LLM ligada, o bot interpreta e cria um rascunho; mostra o resumo e/ou pergunta o que falta.
3. Você revisa: `detalhar N`.
4. `confirmar N` → o bot tenta gravar **se** a escrita estiver habilitada (WRITE_ENABLED=true +
   chave de escrita). Caso contrário, o rascunho fica confirmado, pronto para gravar depois.

## Observações
- Sem persistência (sem volume `/app/data`), os rascunhos não sobrevivem a redeploy — o bot avisa.
- Rascunhos vencem em 48h (viram "cancelado").
- Nada é gravado no BRGlobal sem `confirmar N`.
- **Idempotência:** cada confirmação usa uma Idempotency-Key estável; reenviar não duplica.
- **Não há endpoint de apagar** registro real via agente — remoção é pelo sistema web/restore.
