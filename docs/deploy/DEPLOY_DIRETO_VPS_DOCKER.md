# Deploy direto na VPS — Docker Compose (sem Easypanel)

```
VPS → Docker Compose → container `agentefin` → Telegram (polling)
                                              → BRGlobal API (https://lixo.brglobal.com.br/api/agent/v1)
```

> Bot **somente leitura**, **polling** do Telegram. **Sem porta, sem domínio, sem proxy, sem SSL.**
> Sem scheduler, sem Fase 2, sem novas funcionalidades.
>
> **Forma recomendada de operar:** `bash scripts/ops/agentefin-vps.sh` (menu interativo —
> configura `.env`, deploy/update, logs, restart, validação). Ver `OPERADOR_VPS_INTERATIVO.md`.
> Os passos manuais abaixo continuam válidos como referência.

## 1. Por que não usar Easypanel
A licença gratuita do Easypanel está limitada a **3 projetos** (já em uso). Para não
consumir esse limite, o agente roda como um **serviço Docker Compose simples** direto
na VPS. É mais leve e suficiente: o bot não recebe tráfego de entrada.

## 2. Por que o bot não precisa de porta/domínio
O bot usa **long polling** da API do Telegram: ele **abre conexões de saída** para
`api.telegram.org` e para a API do BRGlobal. **Ninguém precisa acessá-lo de fora.**
Logo: **sem `ports`, sem domínio, sem reverse-proxy, sem certificado**. Menos
superfície de ataque e zero configuração de rede.

## 3. Clonar o repositório na VPS
```bash
cd ~                     # ou o diretório onde você mantém apps
git clone https://github.com/iltondf/agentefin.git
cd agentefin
```
(Atualizações futuras: `git pull` — ver §8.)

## 4. Criar o `.env` no servidor
O `.env` **não** é versionado (contém segredos). Crie-o na VPS:
```bash
cat > .env <<'EOF'
TELEGRAM_BOT_TOKEN=<token novo do BotFather>
ALLOWED_USER_IDS=8646895490
BRGLOBAL_API_BASE_URL=https://lixo.brglobal.com.br/api/agent/v1
BRGLOBAL_API_KEY=<nova chave bgf_live_...>
TZ=America/Sao_Paulo
LLM_ENABLED=false
EOF
chmod 600 .env
```
> ⚠️ Use **token e chave NOVOS** (rotacionados). Nunca cole segredos em commits/docs.

## 5. Subir com Docker Compose
```bash
docker compose build
docker compose up -d
```
Ou use o script pronto (faz pull + build + up + status + logs):
```bash
bash scripts/deploy/vps-docker-deploy.sh
```
Confirme no log a linha: `bot_start base_url=https://lixo.brglobal.com.br/api/agent/v1 ... allowed=1`.

## 6. Ver logs
```bash
docker compose logs --tail=100        # últimas linhas
docker compose logs -f                # acompanhar ao vivo
# ou:
bash scripts/deploy/vps-docker-status.sh
```
Logs vão para stdout (driver json-file, rotação 10MB × 3). **Nunca** logamos token/chave.

## 7. Reiniciar
```bash
docker compose restart                # reinicia o container
# (o serviço sobe sozinho no boot da VPS por causa de restart: unless-stopped)
```

## 8. Atualizar depois de um `git push`
```bash
bash scripts/deploy/vps-docker-deploy.sh
# equivale a:
#   git pull --ff-only && docker compose build && docker compose up -d
```

## 9. Parar o serviço
```bash
docker compose down
# ou:
bash scripts/deploy/vps-docker-stop.sh
```

## 10. Validar no Telegram
Do usuário autorizado (`ALLOWED_USER_IDS=8646895490`), envie ao bot:
```
/ajuda  /whoami  /hoje  /vencidas  /criticas  /proximos7  /resumo  /painel
```
Esperado: `/whoami` mostra a chave/escopos; os demais trazem os dados reais do
BRGlobal (ou “Nenhuma conta… ✅” quando a janela está vazia).

## Pré-requisitos da VPS
- Docker + plugin Compose v2 (`docker compose version`).
- Acesso de saída a `api.telegram.org` e `lixo.brglobal.com.br` (sem MITM de TLS).
- **Apenas UMA instância** do bot pode fazer polling por token (parar a local antes).

## Variáveis de ambiente (resumo)
| Variável | Valor | Obs |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | *(token novo)* | segredo — só no `.env` |
| `ALLOWED_USER_IDS` | `8646895490` | whitelist (vazio = nega todos) |
| `BRGLOBAL_API_BASE_URL` | `https://lixo.brglobal.com.br/api/agent/v1` | — |
| `BRGLOBAL_API_KEY` | *(nova bgf_live_…)* | segredo — só no `.env` |
| `TZ` | `America/Sao_Paulo` | — |
| `LLM_ENABLED` | `false` | LLM desligada |

## Comandos úteis (na VPS, em `~/agentefin`)
```bash
docker compose ps              # status do container
docker compose logs -f         # logs ao vivo (Ctrl+C sai)
docker compose restart         # reiniciar
docker compose down            # parar
```

## Fluxo de atualização (resumo)
1. No PC: ajustar código/docs → `git push origin main`.
2. `ssh root@SEU_HOST` → `cd ~/agentefin`.
3. `bash scripts/ops/agentefin-vps.sh`.
4. Opção **3** (deploy/update) → `git pull --ff-only` + `build` + `up -d`.
