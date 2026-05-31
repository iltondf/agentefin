# Runbook — operação local e validação

## Rodar local
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env     # preencher
python -m main
```
- Sem `TELEGRAM_BOT_TOKEN` → safe boot (loga `telegram_nao_configurado` e encerra).
- Whitelist vazia (`ALLOWED_USER_IDS=`) → ninguém autorizado (silêncio a estranhos).

## Testes
```powershell
pip install -r requirements-dev.txt
python -m pytest -q                 # 26 testes
```

## Smoke de conexão real (descartável)
```powershell
$env:BASE="http://localhost:3334/api/agent/v1"   # API de agentes rodando
.\.venv\Scripts\python.exe _verificar_conexao.py  # sem chave → 401 (auth) tratado
```

## Checklist pós-deploy (no Telegram)
`/ajuda` → `/whoami` (valida a chave) → `/hoje` → `/vencidas` → `/criticas`
→ `/proximos7` → `/resumo` → `/painel`.

## Logs / observabilidade
- Stdout (estruturado `chave=valor`): `bot_start`, `api_call path=... status=... ms=...`,
  `acesso_negado`, `rate_limit`, `cmd_erro kind=...`.
- Nunca logamos token/chave nem conteúdo financeiro.

## Falhas comuns
| Sintoma | Ação |
|---|---|
| Bot não responde a estranho | esperado (whitelist). Adicione o ID em `ALLOWED_USER_IDS`. |
| `🔒 Falha de autenticação` | chave ausente/inválida/expirada — revise `BRGLOBAL_API_KEY`. |
| `🚫 API desabilitada` | `AGENT_API_ENABLED=false` no servidor (kill-switch). |
| `📡 Não consegui falar com a API` | servidor fora do ar / `BRGLOBAL_API_BASE_URL` errada. |
| TLS/SSL ao chamar Telegram | antivírus com "HTTPS scanning" — desligar (não enfraquecer SSL no código). |
