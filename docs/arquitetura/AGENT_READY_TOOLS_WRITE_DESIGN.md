# Agent-Ready — design das tools (read + write). Planejamento, NÃO implementado.

Fonte: `BRGLOBAL_FINANCEIRO_API_AGENT_READY_2026-06-21.md`. Em divergência, **confiar no doc/código**.

## Cliente HTTP — 2 envelopes (ponto crítico)
- **Antigos (seção 5):** recurso em `envelope.data`.
- **Novos (seções 6/7):** sucesso em `envelope.data.data` (`{ok,data,message,warnings,nextAction}`);
  erro em `envelope.error` (`{ok:false,errorCode,precisaConfirmar,message,candidatos,camposFaltando}`).
- O cliente deve ter `_unwrap_legacy()` e `_unwrap_v2()` (ou detectar `ok` em `data`).
- POST: header `Idempotency-Key`; retry só 429/503/504/rede **com a mesma key**; nunca logar a chave.

## Contrato de tool (interno, Python — sem framework)
```
Tool: name · kind (read|write) · description · args_schema (JSON Schema mínimo)
      escopo · endpoint · run(args)->ToolResult · format(data)->str
ToolWrite (extra): build_payload(rascunho) · confirmacao_obrigatoria=True
                   idempotency_key(rascunho) · erros_esperados[]
```
Comando manual e LLM despacham para a MESMA tool. Whitelist fechada (sem http/sql/exec genéricos).

## READ tools (sem confirmação) — resolvem IDs antes de escrever
| Tool | Endpoint | Escopo | Args | Frase exemplo | Resposta (data.data) | Risco |
|---|---|---|---|---|---|---|
| `consultar_whoami` | `GET /whoami` | (Bearer) | — | "minha chave" | apiKey{escopos} | nulo |
| `consultar_contas_hoje/vencidas/criticas` | `GET /contas-pagar/*` | read:financeiro | — | "o que vence hoje" | `{data:[],total}` | nulo |
| `consultar_contas_proximos_dias` | `GET /contas-pagar/proximos-dias` | read:financeiro | dias 1–90 | "próximos 7 dias" | lista | nulo |
| `consultar_resumo_diario` / `consultar_painel_operacional` | `GET /resumo-diario` / `/painel-operacional` | read:financeiro | (painel: contaBancariaId?,mes?) | "resumo"/"painel" | agregado | painel é pesado (1 snapshot) |
| `buscar_funcionarios` | `GET /rh/funcionarios/buscar` | read:rh | nome | "acha o Vanderli" | candidatos+`ambiguo` | desambiguar |
| `buscar_fornecedores` | `GET /financeiro/fornecedores/buscar` | **read:financeiro** | nome | "fornecedor Areião" | candidatos+`ambiguo` | desambiguar |
| `buscar_obras` | `GET /cadastros/obras/buscar` | read:cadastros | nome | "obra Rio de Janeiro" | candidatos | desambiguar |
| `buscar_unidades` | `GET /cadastros/obras/:id/unidades` | read:cadastros | obraId | "unidades da obra 4" | unidades | — |
| `buscar_terceirizados` | `GET /terceirizados/buscar` | read:terceirizados | nome | "Jailton" | candidatos+serviçosAbertos | desambiguar |
| `buscar_servicos_terceirizado` | `GET /terceirizados/servicos/buscar` | read:terceirizados | nome,status? | "serviços do Vitor" | serviços | escolher serviço |
| `detalhar_servico_terceirizado` | `GET /terceirizados/servicos/:id` | read:terceirizados | id | "detalhe do serviço 9" | saldo/pagamentos | — |
| `buscar_contas_bancarias` | `GET /financeiro/contas-bancarias[/buscar]` | read:financeiro | nome? | "conta Caixa" | `{ultimos4}` (sanitizado) | — |
| `consultar_fechamento_rh` | `GET /rh/fechamento[/funcionario]` | read:rh | mes,tipo[,funcionarioId] | "fechamento de junho" | preview | — |
| `consultar_resumo_rh` / `consultar_extrato_rh` | `GET /rh/resumo` / `/rh/extrato` | read:rh | funcionarioId,mes | "extrato do João" | lançamentos | — |
| `buscar_pix` / `buscar_extrato` | `GET /extrato/pix/buscar` / `/extrato/buscar` | read:extrato | valor?,data?,nome?,contaBancariaId? | "pix de 1800 hoje" | candidatos | — |
| `buscar_contas_pagar` | `GET /financeiro/contas-pagar/buscar` | read:financeiro | fornecedor?,status?,obraId? | "conta da Condor" | candidatos+`ambiguo` | desambiguar |

Regra: `ambiguo=true` ou `candidatos.length>1` → **perguntar** antes de qualquer escrita.

## WRITE tools (SEMPRE confirmação humana + Idempotency-Key)
Para cada uma: **endpoint · escopo · payload · obrigatórios · defaults possíveis · perguntar se faltar ·
erros · idempotency · anti-duplicidade · resumo antes de confirmar · pendência se faltar dado.**

### W1 `criar_lancamento_rh` — `POST /rh/lancamentos` · write:rh
- Payload: `{funcionarioId, tipo, destino?, data, qtd, valorUnit, obraId?, obraUnidadeId?, observacao?, confirmarDuplicado?}`
- Tipos: falta|diaria_extra|tarefa|inss_informado|adiantamento|ajuste_positivo|ajuste_negativo. `destino`: vale|pagamento.
- Obrigatórios: funcionarioId(resolver via busca), tipo, data, qtd, valorUnit. **Default:** data=hoje, obra=default, destino=default config; **perguntar** se destino faltar e não houver default confiável.
- Erros: AMBIGUO(func), VALIDACAO, DUPLICADO_PROVAVEL(func+data+tipo+valor → `confirmarDuplicado:true`).
- Idem: `tg:<chat>:<msg>:rh_lanc:<yyyymmddHHMM>`. Resumo: func/tipo/destino/qtd/valorUnit/obra/data.

### W2 `criar_conta_pagar` — `POST /financeiro/contas-pagar` (`pago:false`) · write:financeiro
- Payload: `{fornecedorId, categoriaId, obraId?, obraUnidadeId?, descricao, valor, dataVencimento, dataCompetencia?, observacoes?, pago:false, confirmarDuplicado?}`
- Obrigatórios: fornecedorId(busca), categoriaId, descricao, valor, dataVencimento. **Mão de Obra → obraId obrigatório.**
- Erros: AMBIGUO(fornecedor), VALIDACAO, DUPLICADO_PROVAVEL(fornecedor+valor+venc+descrição).

### W3 `criar_conta_pagar_paga` — idem com `pago:true`
- **Exige** `contaBancariaId + formaPagamento + dataPagamento` (cria CP + baixa oficial). **Default:** dataPagamento=hoje, forma=pix, conta=default; mostrar no resumo. Faltando conta/forma → `FALTA_CONTA_ORIGEM`/`FALTA_FORMA_PAGAMENTO` → perguntar. **Não** altera/cancela CP paga.

### W4 `registrar_pagamento_servico_terceirizado` — `POST /terceirizados/servicos/:id/pagamentos` · write:terceirizados
- Payload: `{valor, dataPagamento, tipo, formaPagamento, contaBancariaId, observacao?, excedenteAutorizado?, motivoExcedente?, confirmarDuplicado?}`. Tipos: adiantamento|pagamento_parcial|pagamento_final|extra_autorizado|material_reembolso.
- Pré-resolução: terceirizado → **serviço aberto** (se >1, perguntar) → conta bancária. Serviço precisa ter obra (servidor herda).
- Erros: FALTA_CONTA_ORIGEM, FALTA_FORMA_PAGAMENTO, SERVICO_FINALIZADO, EXCEDE_VALOR_COMBINADO(`precisaConfirmar`→`excedenteAutorizado:true`+motivo), DUPLICADO_PROVAVEL.

### W5 `criar_servico_terceirizado` — `POST /terceirizados/servicos` · write:terceirizados
- Payload: `{funcionarioId, descricao, valorCombinado, obraId(obrig.), obraUnidadeIds[], dataInicio?, dataPrevisaoFim?, observacoes?, confirmarDuplicado?}`. Func deve ser terceirizado; unidades pertencem à obra.

### W6 `cadastrar_terceirizado` — `POST /terceirizados` · write:terceirizados|cadastros_basico
- Payload: `{nome, funcao, cpfCnpj?, telefone?, chavePix?, obraDefaultId?, confirmarDuplicado?}`. Sem CPF + nome parecido → AMBIGUO → `confirmarDuplicado:true`. Só cadastra.

## Defaults (config simples)
`defaults.yaml` versionado (sem segredo) + overrides em SQLite (aprendizado por uso):
`obraPadraoId`, `contaBancariaPadraoId`, `formaPagamentoPadrao=pix`, `rh.destinoPadrao`,
`rh.funcionarios.<nome>.diariaPadrao/obraPadraoId`, `categorias.<palavra>=<categoriaId>`.
Confiança alta → usar e **mostrar no resumo**; faltou crítico → perguntar.

## Comando manual × LLM
Comandos antigos (seção 5) seguem 0-token e intactos. Novas tools acessíveis por comando explícito
(ex.: `/buscar_funcionario Vanderli`) e por LLM (parser → intent). Mesma camada; LLM nunca executa POST.
