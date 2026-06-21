# Troubleshooting — problemas comuns (agente)

| Sintoma | Causa provável | Solução |
|---|---|---|
| Processo encerra logo após subir | sem `TELEGRAM_BOT_TOKEN` (safe boot) | definir o token no `.env`/Easypanel |
| **Bot não responde a NADA (nem texto livre nem erro); log sem `freeform_in`** | **Token do Telegram COMPARTILHADO** com outro sistema (n8n/WhatsApp/outro bot). Só 1 processo pode fazer `getUpdates` por token — o outro "rouba" as mensagens. | **Usar um token EXCLUSIVO** (criar bot novo no @BotFather) só para o agente; ou remover o token do outro sistema. Conferir webhook: `getWebhookInfo` (deve ter `url` vazio). |
| Bot ignora você | seu ID não está em `ALLOWED_USER_IDS` (vazio = nega todos) | adicionar seu ID numérico (descubra com @userinfobot) |
| Texto livre não vira ação (mas comandos `/` funcionam) | `LLM_ENABLED=false` | ligar `LLM_ENABLED=true` + `OPENROUTER_API_KEY`; ou usar comandos `/rh_teste` etc. |
| `.env` novo não aplica após editar | `docker compose restart` não relê `.env` | recriar: `docker compose up -d --force-recreate` (operador opção 3/6 já fazem) |
| `🔒 Falha de autenticação` | `BRGLOBAL_API_KEY` ausente/inválida/expirada | gerar/rotacionar a chave; conferir env |
| `🔒 sem permissão` (403) | chave sem escopo | gerar chave com `read:financeiro,read:extrato` |
| `🚫 API desabilitada` (503) | kill-switch `AGENT_API_ENABLED=false` no servidor | reabilitar no servidor |
| `endpoint não encontrado` (404) | `BRGLOBAL_API_BASE_URL` errada ou versão sem `/api/agent/v1` | usar base correta (`/api/agent/v1`) da build atual |
| `📡 Não consegui falar com a API` | servidor fora do ar / rede / URL | conferir host e conectividade |
| Erro TLS chamando Telegram | antivírus "HTTPS scanning" | desligar HTTPS scanning (não mexer no SSL do código) |
| `ModuleNotFoundError` ao rodar | venv/deps não instalados | `pip install -r requirements.txt` |
