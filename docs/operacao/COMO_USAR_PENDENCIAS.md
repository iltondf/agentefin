# Como usar Pendências (rascunhos)

O bot captura pedidos rápidos como **rascunho** e só grava após você confirmar.

## Comandos
- `/pendencias` (ou escreva "pendências") — lista os rascunhos ativos.
- `detalhar N` — mostra todos os campos do rascunho N.
- `confirmar N` — marca o rascunho como confirmado (humano OK).
- `cancelar N` — cancela o rascunho N.

## Fluxo
1. Você manda uma frase ("comprei areia R$ 1.800 no Pix").
2. Com LLM ligada, o bot interpreta e cria um rascunho; mostra o resumo e/ou pergunta o que falta.
3. Você revisa: `detalhar N`.
4. `confirmar N` → o bot tenta gravar **se** a escrita estiver habilitada (WRITE_ENABLED=true +
   chave de escrita). Caso contrário, o rascunho fica confirmado, pronto para gravar depois.

## Observações
- Sem persistência (sem volume `/app/data`), os rascunhos não sobrevivem a redeploy — o bot avisa.
- Rascunhos vencem em 48h (viram "cancelado").
- Nada é gravado no BRGlobal sem sua confirmação.
