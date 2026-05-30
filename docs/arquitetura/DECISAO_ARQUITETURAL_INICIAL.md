# Decisão Arquitetural Inicial — Agente Financeiro

> ETAPA 0 (auditoria + decisões). Fonte da verdade do projeto: esta pasta `docs/`.
> Data: 2026-05-30.

## 1. O que é este projeto

Bot de **Telegram somente leitura** que consulta o **BRGlobal Financeiro** pela
API de agentes. Arquitetura explícita e simples:

```
Telegram → Command Router → Finance API Client → BRGlobal API → Resposta
```

Reaproveita o **padrão operacional** do `agente_email` (Telegram/aiogram, config
por env, logs estruturados em stdout, Docker/Easypanel, ritual de Git) **sem**
copiar regra de negócio e **sem** virar framework (ADR-0014 do projeto de referência).

## 2. Auditoria dos projetos de referência (apenas leitura)

- **Arquitetura:** `C:\claude sistemas\agente_email`
  - Padrão consolidado: processo único `python -m main` (bot + opcionalmente
    scheduler), whitelist rígida (`ALLOWED_USER_IDS`, vazio = nega todos), config
    pydantic-settings, logging chave=valor (stdout + arquivo rotacionado), Docker
    `python:3.12-slim` + `tzdata`, volume `/app/data`, deploy GitHub→Easypanel,
    "0-token-first" (determinístico antes de LLM), degradação se a LLM cair.
- **Domínio:** `C:\claude sistemas\bck financeiro 16-05\brglobalfinanceiro`
  (monorepo Node/TS/Fastify/Prisma/MySQL).

## 3. Descoberta importante: discrepância de versão da API

| Projeto | Tem `/api/agent/v1`? | Observação |
|---|---|---|
| `bck financeiro 16-05` (referência citada) | ❌ Não | Expõe `/api/hermes/contas-pagar/*`, `/api/hermes/contas-receber/*` e `/api/*`. Sem API de agentes dedicada. |
| `brglobalfinanceiro` (atual, 28-05) | ✅ Sim | Módulo `agent` → `/api/agent/v1` (Bearer, read-only, escopos, kill-switch, rate-limit, envelope). |

Validado **ao vivo** (ver `docs/operacao/evidencias-testes.md`):
- `bck 16-05` rodando em :3333 → `GET /api/agent/v1/whoami` retorna **404**.
- `brglobalfinanceiro` 28-05 rodando em :3334 → `GET /api/agent/v1/whoami` (sem
  chave) retorna **401** (contrato de agente real e ativo).

**Conclusão:** a API de agentes (`/api/agent/v1`) é o contrato-alvo e existe na
base **atual** do financeiro (28-05). O agente é configurável por env
(`BRGLOBAL_API_BASE_URL`), então aponta para qualquer host/versão implantada.

## 4. Sobre "Hermes" (decisão aprovada: NÃO usar Hermes)

"Hermes" era o **agente/skill de WhatsApp** planejado, construído sobre as rotas
`/api/hermes/*`. A decisão aprovada é **não reconstruir/depender desse runtime,
orquestração ou seleção de modelo**. Reaproveitamos apenas **endpoints,
documentação e conceitos de negócio**.

Materialização: construímos um **bot de Telegram limpo** que consome a API de
agentes dedicada **`/api/agent/v1`** (módulo `agent`, distinto das rotas `hermes`).
Sem n8n, sem orquestração agêntica, sem seleção dinâmica de modelo.

## 5. Problema de ambiente resolvido: "@prisma/client did not initialize yet"

- **Causa:** o Prisma Client nunca foi gerado (`@prisma/client` sem artefato).
  O binário `prisma` existe apenas em `packages/database/node_modules/.bin`, então
  rodar `prisma`/`pnpm exec prisma` a partir da **raiz** falha ("command not found").
- **Solução (read-only, autorizada):** gerar pelo script do workspace:
  ```powershell
  pnpm run db:generate        # = pnpm --filter database generate = prisma generate
  ```
  Resultado: `Generated Prisma Client (v5.22.0)`. API sobe normalmente
  (`/health` → 200, `db: ok`). Nenhuma migration/seed/escrita foi executada.
- Detalhes em `docs/troubleshooting/prisma-monorepo.md`.

## 6. Decisões de arquitetura do agente

1. **Projeto isolado** (`agente_financeiro`), repo próprio (`agentefin`). Não
   adicionamos um 2º agente ao `agente_email` (evita roteamento multi-agente).
2. **Somente leitura** no MVP. Nenhum POST/PATCH/DELETE. O agente nunca acessa o
   banco direto nem recalcula regra financeira — o servidor é a fonte da verdade.
3. **Determinístico (0-token):** todos os comandos resolvem via API + formatação
   em Python puro. **LLM é opcional e desligada por padrão** (`LLM_ENABLED=false`);
   o sistema funciona 100% sem LLM. Ver `docs/decisoes/0002-llm-opcional.md`.
4. **Cliente HTTP robusto:** timeout, retries mínimos só em falhas transitórias
   (GET idempotente), logs estruturados, erros tipados e mensagens de degradação.
5. **Pacote único `financebot/`** (sem split core/agents): é um bot de propósito
   único — abstrair para "plataforma de agentes" seria overengineering.

## 7. Restrição de teste (honesta)

Chamadas autenticadas exigem uma **API Key** (`bgf_*`), cujo registro é um
**INSERT** na tabela `api_keys` — **proibido** nesta tarefa (BRGlobal é read-only).
Portanto:
- **Testes de integração** usam um **stub HTTP local** com o **mesmo envelope** da
  API real (teste over-the-wire).
- **Evidência real:** `/health` 200 e o **contrato 401** real da API de agentes;
  o cliente classifica corretamente o 401 real como `auth` (degradação).
- **Validação autenticada final** (200 com dados reais) é um passo do operador:
  gerar a chave (`pnpm agente:create-key`, escopos `read:financeiro,read:extrato`),
  definir `BRGLOBAL_API_KEY` e `BRGLOBAL_API_BASE_URL`, e rodar `/whoami`.
