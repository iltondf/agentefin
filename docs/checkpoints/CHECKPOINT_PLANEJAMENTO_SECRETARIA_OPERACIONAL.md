# Checkpoint 0007 — Planejamento: Secretária Operacional (inbox + rascunhos)

**Data:** 2026-05-31. **Tipo:** planejamento (sem código/banco/endpoint/deploy).

## Ideia
Evoluir o bot de consulta para **captura operacional**: o admin fala naturalmente, a LLM
interpreta, o agente cria um **rascunho/pendência estruturada**, valida e pede **confirmação/
revisão**; só após confirmação humana o BRGlobal grava via **API própria de agente**.
Nada é lançado por "entendimento" da LLM.

## Auditoria (read-only) — base do plano
- Agent API `/api/agent/v1`: **9 rotas, todas GET** (zero escrita).
- Escopos `write:*` **definidos mas sem endpoint**. Escrita só existe nas **rotas humanas (JWT)**.
- **Não existe** tabela de inbox/rascunho/pendência no BRGlobal.

## Arquitetura recomendada
`Telegram → LLM interpreta → agente monta RASCUNHO (valida) → resume e pede confirmação →
[após confirmação humana] API grava`. Camadas do barato→arriscado: pendência textual →
inbox → busca/desambiguação → rascunho por domínio → confirmação que grava.

## Veredito
**APROVAR COM CUIDADO**, faseado:
1. **Agora (zero BRGlobal):** "mensagem para a secretária" — bot resume o pedido em texto pronto, **sem gravar**.
2. **MVP:** **inbox textual** no BRGlobal (1 tabela + 3-4 rotas agent, `write:inbox`/`read:inbox`).
3. **Depois:** busca/desambiguação → rascunhos por domínio → confirmação que grava (`confirm:*`, idempotência, auditoria).
**Não** gravar lançamento/baixa direto pelo bot.

## MVP recomendado
**Inbox textual estruturada** (criar/listar/cancelar pendência) — esforço baixo, risco baixo,
valor alto, base para tudo. Passo 0 imediato sem tocar BRGlobal: "mensagem p/ secretária".

## Guardrails (obrigatórios)
LLM interpreta/extrai/resume; **nunca** grava/confirma/escolhe ambíguo/calcula valor final.
Toda escrita: confirmação humana + idempotency-key + auditoria + endpoint/escopo de agente
próprios; chave read-only **não** escreve. Ver `docs/seguranca/WRITE_TOOLS_GUARDRAILS.md`.

## Documentos criados
- `docs/roadmap/PLANO_SECRETARIA_OPERACIONAL.md`
- `docs/arquitetura/INBOX_OPERACIONAL_DESIGN.md`
- `docs/seguranca/WRITE_TOOLS_GUARDRAILS.md`

## Estado
Agente **em produção** no MVP read-only. Tudo aqui é **plano** — nada implementado;
`.env`/container/BRGlobal/banco/scheduler intocados; LLM desligada.

## Próximo passo
Aprovar o veredito. Se sim: começar pelo **passo 0** ("mensagem p/ secretária", sem escrita)
ou pelo **MVP inbox** (exige decisão de criar 1 tabela + rotas de agente no BRGlobal). Só após autorização.
