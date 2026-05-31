# Operador interativo da VPS — `agentefin-vps.sh`

Menu único para **configurar** o agente e **operar** o container, sem editar
arquivos à mão. Roda na VPS por SSH.

```bash
bash scripts/ops/agentefin-vps.sh
```

## Acesso à VPS e localização do projeto
```bash
ssh root@SEU_HOST            # ex.: ssh root@srv822821
cd ~/agentefin               # projeto clonado em /root/agentefin
bash scripts/ops/agentefin-vps.sh
```
- Repositório: `https://github.com/iltondf/agentefin.git` (clonado em `~/agentefin`).
- O `.env` (segredos) fica em `~/agentefin/.env` — **nunca** versionado.

## Menu
```
1) Verificar ambiente
2) Configurar variáveis do agente (.env)   <- assistente
3) Fazer deploy/update
4) Ver status
5) Ver logs
6) Reiniciar bot
7) Parar bot
8) Validar API BRGlobal (/whoami)
9) Mostrar checklist Telegram
0) Sair
```

## Opção 2 — Configurar `.env` (assistente)
Cria/atualiza o `.env` **campo a campo**, sem abrir editor:
- pré-carrega os valores atuais (se o `.env` existir);
- **faz backup** antes de salvar: `.env.bak.AAAAMMDD-HHMMSS` (gitignored);
- para cada variável mostra nome + descrição + valor atual (**segredos mascarados**);
- **ENTER mantém** o valor atual; digitar substitui;
- **segredos** (`TELEGRAM_BOT_TOKEN`, `BRGLOBAL_API_KEY`, `OPENROUTER_API_KEY`) usam
  entrada **oculta** (`read -s`) e **nunca** são impressos por completo;
- valida obrigatórios e regras de LLM;
- salva com `chmod 600`;
- pergunta se quer **reiniciar o bot** agora.

### Variáveis
**Obrigatórias:** `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`, `BRGLOBAL_API_BASE_URL`,
`BRGLOBAL_API_KEY`, `TZ`, `LLM_ENABLED`.
**Opcionais/futuras:** `LLM_PROVIDER`, `LLM_MODEL`, `OPENROUTER_API_KEY`,
`HTTP_TIMEOUT`, `HTTP_RETRIES`, `RATE_LIMIT_PER_MIN`, `LOG_LEVEL`.

> **Nota LLM (futuro/Fase 2):** os campos `LLM_PROVIDER`/`OPENROUTER_API_KEY` ficam
> preparados no `.env`, mas a LLM está **desligada** (`LLM_ENABLED=false`) e o bot
> atual **não** consome esses campos ainda (a integração LLM é trabalho de Fase 2).

### Trocar o token do Telegram
Opção 2 → no campo `TELEGRAM_BOT_TOKEN` cole o **token novo** (entrada oculta) →
demais campos ENTER → confirmar reiniciar. Pronto.

### Trocar a `BRGLOBAL_API_KEY`
Opção 2 → no campo `BRGLOBAL_API_KEY` cole a **chave nova** (oculta) → reiniciar.
Depois valide com a **opção 8**.

### Habilitar/desabilitar LLM (futuro)
Opção 2 → `LLM_ENABLED=true` exige `LLM_PROVIDER`; se `openrouter`, exige
`OPENROUTER_API_KEY`. Para desligar: `LLM_ENABLED=false` (chave/modelo podem ficar vazios).

## Opção 3 — Deploy/Update
Aborta se houver alterações locais não commitadas; senão:
`git pull --ff-only origin main` → `docker compose build` → `up -d` → `ps` + logs.
Exige `.env` presente (configure na opção 2 antes). **Não** pede token aqui.

## Opção 4/5 — Status / Logs
`docker compose ps` + `logs --tail=100` / `logs --tail=200`. Logs vão para stdout.

## Opção 6/7 — Reiniciar / Parar
`docker compose restart` (+ ps + logs) / `docker compose down`.

## Opção 8 — Validar API
Lê `BRGLOBAL_API_BASE_URL` + `BRGLOBAL_API_KEY` do `.env`, chama `GET /whoami` com
Bearer e mostra status + nome/prefixo/escopos/ambiente (**sem** imprimir a chave):
- `200` = válida · `401` = inválida/revogada · `403` = escopo insuficiente ·
  `404` = URL errada/sem `/api/agent/v1` · `timeout/000` = rede/API.

## Rollback do `.env` (usar backup)
```bash
ls -1 .env.bak.*              # listar backups
cp .env.bak.AAAAMMDD-HHMMSS .env
chmod 600 .env
docker compose restart
```

## Segurança
`set -Eeuo pipefail`, sem `set -x`. Nunca imprime token/chave. `.env` e `.env.bak.*`
são **gitignored** (`.env.*`). Sem operações destrutivas globais (sem `prune`/`volume rm`).
Sem chamadas de escrita à API; sem mexer no BRGlobal/banco; sem scheduler/Fase 2.
