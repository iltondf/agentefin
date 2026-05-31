# Checkpoint 0004 — Operador interativo da VPS

**Data:** 2026-05-31.

## Marco
Adicionado `scripts/ops/agentefin-vps.sh`: **menu interativo** que serve, sobretudo,
como **assistente de configuração do `.env`** (trocar token/chave/LLM sem editor) e
para operar o container (deploy/update, status, logs, restart, stop, validar API).

## Itens
- Opções 1–9 (+ 0 sair). Opção 2 = assistente `.env` (foco principal).
- `.env`: pré-carrega atuais, **backup** `.env.bak.*` antes de salvar, prompts campo a
  campo, **segredos com `read -s`** e **mascarados** na exibição, `chmod 600`, validações
  (obrigatórios; `LLM_ENABLED` true/false; se true exige provider e, p/ openrouter, a chave).
- Opção 8 valida `/whoami` (Bearer) e traduz 200/401/403/404/timeout — **sem imprimir a chave**.
- Segurança: `set -Eeuo pipefail`, sem `set -x`, sem `prune`/`volume rm`, sem escrita na API.
- LLM permanece **futura/desligada** — o bot **não** foi alterado (sem novas funcionalidades).

## Validações
- `bash -n` OK nos 4 scripts (`ops/agentefin-vps.sh` + 3 de deploy). shellcheck: não instalado (opcional).
- `pytest` 26 passed. `.env*` gitignored; nenhum segredo versionado; `*.sh` em LF.

## Docs
- `docs/deploy/OPERADOR_VPS_INTERATIVO.md` (guia completo: configurar, trocar token/chave,
  LLM futuro, deploy, logs, restart, parar, validar, **rollback via backup**).

## Pendências (inalteradas)
Rotacionar token+chave, criar `.env` na VPS (via opção 2), subir, testar 8 comandos,
revogar chave antiga id 7. Deploy real **não** executado.
