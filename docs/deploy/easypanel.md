# Deploy — Easypanel (Docker)

Padrão herdado do ecossistema de agentes: build do GitHub via `Dockerfile`,
processo único, **sem porta de entrada**, variáveis pela interface.

## Passos
1. **Repo:** `https://github.com/iltondf/agentefin.git`, branch `main`.
2. **Projeto:** criar (ex.: `agente-financeiro`).
3. **Serviço → App:** Source = GitHub (este repo), Build = **Dockerfile**.
   Não definir porta nem domínio (só conexões de saída).
4. **Environment (variáveis):**
   - `TELEGRAM_BOT_TOKEN` (BotFather)
   - `ALLOWED_USER_IDS` (IDs numéricos separados por vírgula; vazio = nega todos)
   - `BRGLOBAL_API_BASE_URL` (ex.: `https://SEU-HOST/api/agent/v1`)
   - `BRGLOBAL_API_KEY` (`bgf_live_*`)
   - opcional: `DEFAULT_CONTA_BANCARIA_ID`, `HTTP_TIMEOUT`, `RATE_LIMIT_PER_MIN`,
     `TZ=America/Sao_Paulo`, `LOG_LEVEL`
   - LLM (opcional): `LLM_ENABLED=true`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
5. **Volume (opcional):** montar em `/app/data` se quiser persistir o arquivo de log
   (logs primários já vão para stdout).
6. **Deploy:** build automático. Conferir no log: `bot_start base_url=... allowed=N`.
7. **Update:** a cada `git push`, "Deploy/Rebuild".

## Notas
- `tzdata` já vem na imagem (TZ correto). `PYTHONUNBUFFERED=1` → logs ao vivo.
- Nenhum segredo no Git/imagem — tudo vem das variáveis do Easypanel.
- Não há OAuth/credencial em arquivo (diferente do agente Gmail): só a env
  `BRGLOBAL_API_KEY`. Por isso o volume é **opcional**.
