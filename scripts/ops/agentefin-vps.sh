#!/usr/bin/env bash
# Operador interativo do agente_financeiro na VPS.
# Foco: configurar o .env SEM editor (assistente campo-a-campo) + operar o container
# (deploy/update, status, logs, restart, stop, validar API).
#
# Segurança: set -Eeuo pipefail; NUNCA imprime segredos; backup do .env antes de
# sobrescrever; chmod 600; sem operações destrutivas globais (sem prune/volume rm).
set -Eeuo pipefail

if [ -z "${BASH_VERSION:-}" ]; then echo "Use bash para rodar este script." >&2; exit 1; fi
if ((BASH_VERSINFO[0] < 4)); then echo "Requer bash 4+ (arrays associativos)." >&2; exit 1; fi
trap 'rc=$?; [ $rc -ne 0 ] && echo "✖ erro inesperado (rc=$rc, linha $LINENO)" >&2' ERR

# Raiz do projeto (este script está em scripts/ops/)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
ENV_FILE="$ROOT/.env"

# Ordem das variáveis no .env
KEYS=(TELEGRAM_BOT_TOKEN ALLOWED_USER_IDS BRGLOBAL_API_BASE_URL BRGLOBAL_API_KEY TZ \
      LLM_ENABLED LLM_PROVIDER LLM_MODEL OPENROUTER_API_KEY \
      HTTP_TIMEOUT HTTP_RETRIES RATE_LIMIT_PER_MIN LOG_LEVEL)

declare -A CUR   # valores atuais carregados do .env
declare -A NEW   # valores a salvar

is_secret()   { case "$1" in TELEGRAM_BOT_TOKEN|BRGLOBAL_API_KEY|OPENROUTER_API_KEY) return 0;; *) return 1;; esac; }
is_required() { case "$1" in TELEGRAM_BOT_TOKEN|ALLOWED_USER_IDS|BRGLOBAL_API_BASE_URL|BRGLOBAL_API_KEY|TZ|LLM_ENABLED) return 0;; *) return 1;; esac; }

default_for() {
  case "$1" in
    ALLOWED_USER_IDS)       echo "8646895490";;
    BRGLOBAL_API_BASE_URL)  echo "https://lixo.brglobal.com.br/api/agent/v1";;
    TZ)                     echo "America/Sao_Paulo";;
    LLM_ENABLED)            echo "false";;
    LLM_PROVIDER)           echo "openrouter";;
    HTTP_TIMEOUT)           echo "20";;
    HTTP_RETRIES)           echo "2";;
    RATE_LIMIT_PER_MIN)     echo "30";;
    LOG_LEVEL)              echo "INFO";;
    *)                      echo "";;
  esac
}

desc_for() {
  case "$1" in
    TELEGRAM_BOT_TOKEN)     echo "Token do bot no Telegram (BotFather). SEGREDO.";;
    ALLOWED_USER_IDS)       echo "IDs Telegram autorizados (vírgula). Vazio = nega todos.";;
    BRGLOBAL_API_BASE_URL)  echo "Base da API de agentes do BRGlobal.";;
    BRGLOBAL_API_KEY)       echo "Chave Bearer do agente (bgf_live_/bgf_test_). SEGREDO.";;
    TZ)                     echo "Fuso horário do container.";;
    LLM_ENABLED)            echo "Liga/desliga a LLM (true/false). Padrão false.";;
    LLM_PROVIDER)           echo "Provedor LLM (ex.: openrouter). Só usado se LLM_ENABLED=true.";;
    LLM_MODEL)              echo "Modelo LLM (ex.: deepseek/...). Opcional.";;
    OPENROUTER_API_KEY)     echo "Chave do OpenRouter. SEGREDO. Só se provider=openrouter.";;
    HTTP_TIMEOUT)           echo "Timeout (s) das chamadas à API.";;
    HTTP_RETRIES)           echo "Retries em falhas transitórias.";;
    RATE_LIMIT_PER_MIN)     echo "Limite de mensagens/min por usuário.";;
    LOG_LEVEL)              echo "Nível de log (INFO/DEBUG/WARNING).";;
    *)                      echo "";;
  esac
}

mask() {
  local v="${1:-}"; local n=${#v}
  if [ "$n" -eq 0 ]; then echo "(vazio)"; return; fi
  if [ "$n" -le 12 ]; then echo "***"; return; fi
  printf '%s...%s' "${v:0:12}" "${v: -3}"
}

load_env() {
  CUR=()
  [ -f "$ENV_FILE" ] || return 0
  local line k val
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|\#*) continue;; esac
    [[ "$line" == *=* ]] || continue
    k="${line%%=*}"; val="${line#*=}"
    k="${k//[[:space:]]/}"
    CUR["$k"]="$val"
  done < "$ENV_FILE"
}

prompt_var() {
  local key="$1"
  local cur="${CUR[$key]-}"
  local def; def="$(default_for "$key")"
  local shown="$cur"; [ -z "$shown" ] && shown="$def"
  local req=""; is_required "$key" && req=" (obrigatório)"
  echo
  echo "• $key$req — $(desc_for "$key")"
  if is_secret "$key"; then
    if [ -n "$cur" ]; then echo "  atual: $(mask "$cur")"; else echo "  atual: (vazio)"; fi
    local input=""
    read -rs -p "  novo valor [ENTER mantém | digite — oculto]: " input || true
    echo
    if [ -n "$input" ]; then NEW["$key"]="$input"; else NEW["$key"]="$cur"; fi
  else
    echo "  atual: ${shown:-(vazio)}"
    local input=""
    read -r -p "  novo valor [ENTER mantém]: " input || true
    if [ -n "$input" ]; then NEW["$key"]="$input"; else NEW["$key"]="$shown"; fi
  fi
}

validate_env() {
  local ok=1 req
  for req in TELEGRAM_BOT_TOKEN ALLOWED_USER_IDS BRGLOBAL_API_BASE_URL BRGLOBAL_API_KEY TZ LLM_ENABLED; do
    if [ -z "${NEW[$req]-}" ]; then echo "  ⚠ obrigatório vazio: $req"; ok=0; fi
  done
  case "${NEW[LLM_ENABLED]-}" in true|false) ;; *) echo "  ⚠ LLM_ENABLED deve ser 'true' ou 'false'"; ok=0;; esac
  if [ "${NEW[LLM_ENABLED]-}" = "true" ]; then
    [ -z "${NEW[LLM_PROVIDER]-}" ] && { echo "  ⚠ LLM_ENABLED=true exige LLM_PROVIDER"; ok=0; }
    if [ "${NEW[LLM_PROVIDER]-}" = "openrouter" ] && [ -z "${NEW[OPENROUTER_API_KEY]-}" ]; then
      echo "  ⚠ provider 'openrouter' exige OPENROUTER_API_KEY"; ok=0
    fi
    [ -z "${NEW[LLM_MODEL]-}" ] && echo "  ℹ aviso: LLM_MODEL vazio (LLM ligada sem modelo)"
  fi
  [ "$ok" -eq 1 ]
}

backup_env() {
  [ -f "$ENV_FILE" ] || return 0
  local ts; ts="$(date +%Y%m%d-%H%M%S)"
  cp -p "$ENV_FILE" "$ENV_FILE.bak.$ts"
  chmod 600 "$ENV_FILE.bak.$ts" 2>/dev/null || true
  echo "  backup criado: .env.bak.$ts"
}

save_env() {
  local tmp; tmp="$(mktemp)"
  local k
  for k in "${KEYS[@]}"; do printf '%s=%s\n' "$k" "${NEW[$k]-}" >> "$tmp"; done
  mv "$tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

configure_env() {
  echo "== Configurar variáveis do agente (.env) =="
  load_env
  NEW=()
  if [ -f "$ENV_FILE" ]; then echo "  .env existente — valores atuais pré-carregados (segredos mascarados)."
  else echo "  .env não existe — será criado."; fi
  local k
  for k in "${KEYS[@]}"; do prompt_var "$k"; done
  echo
  if ! validate_env; then echo "  ❌ Validação falhou. .env NÃO foi alterado."; return 1; fi
  backup_env
  save_env
  echo "  ✅ .env salvo (chmod 600). Resumo (mascarado):"
  for k in "${KEYS[@]}"; do
    if is_secret "$k"; then echo "     $k=$(mask "${NEW[$k]-}")"; else echo "     $k=${NEW[$k]-}"; fi
  done
  echo
  local ans=""
  read -r -p "Deseja reiniciar o bot agora? [s/N]: " ans || true
  case "${ans,,}" in s|sim|y|yes) restart_bot;; *) echo "  (não reiniciado)";; esac
}

check_env() {
  echo "== Verificar ambiente =="
  local c
  for c in git docker curl; do
    if command -v "$c" >/dev/null 2>&1; then echo "  ✅ $c presente"; else echo "  ❌ $c ausente"; fi
  done
  if docker compose version >/dev/null 2>&1; then echo "  ✅ docker compose v2"; else echo "  ❌ docker compose v2 ausente"; fi
  [ -f "$ROOT/Dockerfile" ] && echo "  ✅ Dockerfile" || echo "  ❌ Dockerfile ausente"
  [ -f "$ROOT/docker-compose.yml" ] && echo "  ✅ docker-compose.yml" || echo "  ❌ docker-compose.yml ausente"
  if [ -f "$ENV_FILE" ]; then
    echo "  ✅ .env existe (perm $(stat -c '%a' "$ENV_FILE" 2>/dev/null || echo '?'))"
  else
    echo "  ⚠ .env não existe — use a opção 2"
  fi
  local n
  n="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c '^agentefin$' || true)"
  echo "  containers 'agentefin' ativos: ${n:-0}"
  [ "${n:-0}" -gt 1 ] && echo "  ⚠ mais de um container agentefin — risco de polling duplicado"
  if curl -fsS -m 8 https://api.telegram.org >/dev/null 2>&1; then echo "  ✅ conectividade api.telegram.org"; else echo "  ⚠ sem conectividade/TLS com api.telegram.org"; fi
  load_env
  local base="${CUR[BRGLOBAL_API_BASE_URL]-}"
  if [ -n "$base" ]; then
    local host="${base%/api/agent/v1}"
    if curl -fsS -m 8 "$host/health" >/dev/null 2>&1; then echo "  ✅ BRGlobal /health ok"; else echo "  ⚠ BRGlobal /health falhou ($host)"; fi
  fi
}

deploy_update() {
  echo "== Deploy / Update =="
  [ -f "$ENV_FILE" ] || { echo "  ❌ .env ausente — configure (opção 2) antes de subir."; return 1; }
  echo "  diretório: $ROOT"
  if [ -n "$(git status --porcelain)" ]; then
    echo "  ❌ Há alterações locais não commitadas — abortando (evita conflito com git pull)."
    git status --short
    return 1
  fi
  echo "  -> git pull --ff-only origin main"; git pull --ff-only origin main
  echo "  -> docker compose build";          docker compose build
  echo "  -> docker compose up -d";           docker compose up -d
  docker compose ps
  docker compose logs --tail=50
}

restart_bot() {
  echo "== Reiniciar bot =="
  docker compose restart
  docker compose ps
  docker compose logs --tail=50
}

validate_api() {
  echo "== Validar API BRGlobal (/whoami) =="
  load_env
  local base="${CUR[BRGLOBAL_API_BASE_URL]-}" key="${CUR[BRGLOBAL_API_KEY]-}"
  [ -n "$base" ] || { echo "  ❌ BRGLOBAL_API_BASE_URL vazio (opção 2)"; return 1; }
  [ -n "$key" ]  || { echo "  ❌ BRGLOBAL_API_KEY vazio (opção 2)"; return 1; }
  command -v curl >/dev/null 2>&1 || { echo "  ❌ curl ausente"; return 1; }
  local body status
  body="$(mktemp)"
  status="$(curl -s -m 15 -o "$body" -w '%{http_code}' -H "Authorization: Bearer $key" "$base/whoami" 2>/dev/null || echo 000)"
  case "$status" in
    200)
      echo "  ✅ 200 OK (chave válida)"
      grep -o '"nome":"[^"]*"'        "$body" | head -n1 | sed 's/^/     /' || true
      grep -o '"prefixo":"[^"]*"'     "$body" | head -n1 | sed 's/^/     /' || true
      grep -o '"escopos":\[[^]]*\]'   "$body" | head -n1 | sed 's/^/     /' || true
      grep -o '"environment":"[^"]*"' "$body" | head -n1 | sed 's/^/     /' || true
      ;;
    401) echo "  ❌ 401 — chave inválida ou revogada";;
    403) echo "  ❌ 403 — escopo insuficiente";;
    404) echo "  ❌ 404 — URL errada ou API sem /api/agent/v1";;
    000) echo "  ❌ timeout/rede — verifique conectividade/API";;
    *)   echo "  ⚠ HTTP $status";;
  esac
  rm -f "$body"
}

checklist_telegram() {
  cat <<'EOF'
== Checklist Telegram (do usuário autorizado) ==
  /ajuda      -> lista de comandos
  /whoami     -> identifica a chave (nome/escopos)
  /hoje       -> contas a pagar vencendo hoje
  /vencidas   -> contas vencidas em aberto
  /criticas   -> contas críticas (prioridade alta)
  /proximos7  -> a vencer nos próximos 7 dias
  /resumo     -> resumo diário
  /painel     -> painel operacional consolidado
EOF
}

menu() {
  while true; do
    cat <<'EOF'

==== Operador agentefin (VPS) ====
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
EOF
    local opt=""
    read -r -p "Opção: " opt || { echo; exit 0; }
    case "$opt" in
      1) check_env || true;;
      2) configure_env || true;;
      3) deploy_update || true;;
      4) { docker compose ps && docker compose logs --tail=100; } || true;;
      5) docker compose logs --tail=200 || true;;
      6) restart_bot || true;;
      7) docker compose down || true;;
      8) validate_api || true;;
      9) checklist_telegram || true;;
      0) echo "Saindo."; exit 0;;
      *) echo "Opção inválida.";;
    esac
  done
}

menu
