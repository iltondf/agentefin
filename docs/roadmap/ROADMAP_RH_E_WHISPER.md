# Roadmap — RH via Telegram + Áudio (Whisper)

> Status: **planejado, NÃO implementado.** Registrado no fechamento da fase "Contas a Pagar"
> (2026-06-21). A próxima sessão começa pela **Fase RH**. Whisper é fase posterior.

## Contexto
A fase de **Contas a Pagar** (conta paga, compra paga, fornecedor, defaults, Pix, rascunho,
confirmação humana, POST real, idempotência) está **operacional e validada** em produção
(bot `agenteclaudio`, contaPagarId **932**). Ver `EVIDENCIAS_AGENT_READY_LLM_TELEGRAM_TESTS.md`
e `checkpoints/CHECKPOINT_FECHAMENTO_SESSAO_AGENT_READY_CONTAS_PAGAR.md`.

O fluxo de **RH** já existe no código (intent `criar_lancamento_rh`, `resolve._rh`, tool
`registrar_lancamento_rh`, comando manual `/rh_teste`), mas **não foi validado ponta a ponta
pelo Telegram com LLM hoje**. Não tratar RH como concluído.

---

## Fase 1 (próxima sessão) — RH via Telegram

### Objetivo
Permitir frases naturais como:
- "Vanderli fez duas diárias de R$ 120 no pagamento."
- "Coloca R$ 200 de vale para Edson."
- "Edson fez uma diária hoje."
- "Vanderli trabalhou sábado, diária de R$ 120."
- "Soma 325 + 325 e lança para Vanderli no pagamento."

### A validar (cada item com teste + evidência)
- [ ] Busca de funcionário (nome → id).
- [ ] Funcionário **ambíguo** → perguntar qual (não inventar id).
- [ ] Destino **vale** vs **pagamento** (e destino padrão `rh.destinoPadrao=pagamento`).
- [ ] Diária (qtd × valor unitário).
- [ ] Ajuste positivo.
- [ ] Adiantamento / vale.
- [ ] Valor unitário e **quantidade**.
- [ ] Data (determinística: hoje/data citada).
- [ ] Obra padrão.
- [ ] Rascunho + **confirmação humana**.
- [ ] **POST real pequeno** (R$ 1, `[TESTE_AGENT_READY]`) com Idempotency-Key.
- [ ] Idempotência / ausência de duplicidade.
- [ ] Visualização do lançamento no sistema web + recuperação via GET.

### Notas técnicas (já existentes no código)
- Intent: `criar_lancamento_rh`; resolução em `financebot/resolve.py::_rh`.
- Datas: usar `resolver_data(texto, padrão)` (texto cru manda; ignora ano alucinado pela LLM).
- Tool de escrita: `registrar_lancamento_rh` (gating: WRITE_ENABLED+chave, rascunho confirmado, payload válido).
- Comando manual de fallback (sem LLM): `/rh_teste <funcionario> <tipo> <vale|pagamento> <valor> [data]`.
- GET de apoio: `rh/funcionarios/buscar`, `rh/fechamento`, `rh/resumo`, `rh/extrato`.

### Riscos/ajustes esperados
- Mapear vocabulário ("diária", "vale", "adiantamento", "produção") → `tipo`/`destino` corretos.
- Confirmar o contrato de escrita RH (campos obrigatórios) antes do POST real.
- Evitar vazamento de campos irrelevantes no resumo (mesmo cuidado do `_sanitizar_fields`).

---

## Fase 2 (posterior) — Terceirizados
Não validado hoje. Já há tools (`criar_servico_terceirizado`,
`registrar_pagamento_servico_terceirizado`, buscas). Validar ponta a ponta depois do RH.

---

## Fase 3 (futuro) — Áudio via Telegram (Whisper)

> **Não implementar agora.** Só após o fluxo por **texto** (contas + RH) estar redondo.

### Objetivo
Usuário manda **áudio** no Telegram → agente transcreve → **reaproveita o mesmo pipeline de texto**
(LLM → rascunho → resumo → confirmação humana → POST). O áudio é só uma nova **entrada**; o núcleo
(parser/resolve/drafts/confirmação/escrita) não muda.

### Requisitos
- Aceitar mensagens de **voz/áudio** do Telegram (`voice`/`audio`).
- Baixar o arquivo com segurança (via API do Telegram).
- Transcrever via **Whisper/OpenRouter** (provider configurável).
- **Nunca** enviar tokens/chaves para logs.
- **Limitar tamanho/duração** do áudio (rejeitar acima do limite).
- **Reaproveitar o mesmo parser de texto** (transcrição → `parser.parse`).
- Registrar evidências (transcrição vs interpretação).
- **Fallback** claro se a transcrição falhar (pedir para repetir/digitar).

### Princípios de segurança (manter)
- Confirmação humana obrigatória antes de qualquer POST (áudio não burla o guardrail).
- Segredos só via `.env`/ambiente; nunca em código, log ou transcrição salva.
- Consumir **só** `/api/agent/v1` (sem banco/SQL/Prisma/rotas humanas).

---

## Princípios que NÃO mudam (qualquer fase)
1. `mensagem → LLM → rascunho → resumo → confirmação humana → POST com Idempotency-Key`.
   **Proibido**: mensagem → POST direto.
2. Determinístico e 0-token-first onde der; LLM é parser conversacional.
3. Escrita gated (WRITE_ENABLED + write key + rascunho confirmado + payload válido).
4. Sem framework agêntico; sem tocar o banco do BRGlobal.
