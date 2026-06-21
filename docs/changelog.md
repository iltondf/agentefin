# Changelog

Formato: data — fase — mudança.

## 2026-06-21 — Linguagem natural (LLM) como fluxo principal no Telegram

- **Frase livre → LLM parser → rascunho → resolve (IDs+defaults) → resumo → confirmar/cancelar
  natural → POST.** Parser com prompt robusto (RH/conta pendente/conta paga, `categoriaPalavra`,
  valores BR), **modelo fallback `openai/gpt-4o-mini`** (`LLM_MODEL` vazio), `response_format=json_object`.
- **Confirmação/cancelamento natural** sem número: "confirmar"/"sim"/"ok" e "cancelar"/"não"
  agem no único rascunho aberto (vários → pede o número). Resumo amigável mostra **defaults usados**
  ("Usei obra padrão: 4", "categoria provável: 15", "conta padrão: 5", "forma: pix").
- `defaults.yaml` preenchido (obra 4, conta 5, categorias→15, rh.destinoPadrao=pagamento).
- **64 testes** (parser request/parse, confirm/cancel natural, categoriaPalavra+defaults).
  Docs: `COMO_USAR_LLM_TELEGRAM.md`, `EVIDENCIAS_AGENT_READY_LLM_TELEGRAM_TESTS.md`. Comandos
  manuais seguem como fallback. Ativação da LLM = `.env` da VPS (OPENROUTER_API_KEY).

## 2026-06-21 — Fluxo Telegram ligado + validação real de escrita

- **`confirmar N` agora EXECUTA a escrita**: resolve nomes→IDs (busca), valida, `POST` com
  Idempotency-Key, atualiza rascunho (executado/erro). `corrigir N <campo> <valor>`,
  `cancelar N` (não toca no BRGlobal), comandos manuais `/rh_teste`,`/cp_teste`,`/conta_paga_teste`
  (criam rascunho sem LLM). Novo `resolve.py` (nomes→IDs + defaults). `truststore` (TLS local).
- **POSTs reais autorizados** (`AUTORIZO_POST_REAL_AGENT_READY` + backup): RH **#291**, conta a
  pagar **#929** (pendente) e **#930** (paga), `[TESTE_AGENT_READY]` R$ 1,00; idempotência OK
  (replay não duplica; conflito→409); sem duplicidade. **Não há endpoint de apagar** via agente.
- **57 testes** (6 de fluxo Telegram novos). Docs: `EVIDENCIAS_AGENT_READY_TELEGRAM_TESTS.md` +
  `COMO_USAR_*` atualizados. `WRITE_ENABLED`/`LLM_ENABLED` seguem false no `.env`. Deploy VPS
  pendente (sem SSH). ⚠️ rotacionar chave write id 17.

## 2026-06-21 — Implementação Agent-Ready (tools + rascunhos + parser LLM)

- **Cliente HTTP 2-envelopes** (legacy `data` / v2 `data.data`+`error`); chaves **read/write
  separadas**; idempotência; retry seguro. **Comandos antigos preservados** (0 token).
- **Registry de tools** (21 read: antigas + novas v2) e **6 write tools** com **tripla trava**
  (WRITE_ENABLED+chave, confirmação humana, payload válido) + Idempotency-Key.
- **Rascunhos SQLite** (`fin_draft` em `/app/data`, volume no compose) + comandos
  `/pendencias`,`detalhar/confirmar/cancelar N`. **Defaults** (`defaults.yaml`). **LLM parser**
  (JSON, off por padrão). **Operador VPS** com novas envs + validar /whoami escrita (sem POST).
- **51 testes** passando; `bash -n` OK. `WRITE_ENABLED=false`, `LLM_ENABLED=false` por padrão.
  **POST real NÃO executado.** Docs: `*_IMPLEMENTADO.md`, `WRITE_RUNTIME_GUARDRAILS.md`,
  `COMO_USAR_*`, `EVIDENCIAS_AGENT_READY_WRITE_TESTS.md`; checkpoint 0009.

## 2026-06-21 — Planejamento Agent-Ready (write tools + rascunhos + confirmação)

- **Planejamento (sem código/.env/deploy/LLM/POST).** Spec `BRGLOBAL_FINANCEIRO_API_AGENT_READY_2026-06-21.md`
  copiada para a raiz (fonte da verdade). BRGlobal ficou agent-ready (consulta + escrita controlada).
- Decisões: **1 bot** com modos internos; **LLM = parser** JSON (não executor); **escrita só após
  confirmação humana + Idempotency-Key**; **rascunhos em SQLite** (volume `/app/data`); **2 chaves**
  (read-only atual + nova write); envelope **duplo** (antigos `data`, novos `data.data`).
- Read tools novas (resolvem IDs) + 6 write tools planejadas; `fechamento→CP` = 501 (fica no web).
- Docs: `roadmap/PLANO_AGENT_READY_FASE_WRITE.md`, `arquitetura/AGENT_READY_TOOLS_WRITE_DESIGN.md`,
  `arquitetura/RASCUNHOS_PENDENCIAS_DESIGN.md`, `seguranca/WRITE_CONFIRMATION_GUARDRAILS.md`,
  `seguranca/LLM_PARSER_GUARDRAILS.md`; checkpoint 0008 (consolida 0006/0007 com a API real).

## 2026-05-31 — Planejamento da Secretária Operacional (inbox + rascunhos)

- **Planejamento (sem código/banco/endpoint/deploy).** Captura operacional via Telegram:
  LLM interpreta → agente cria **rascunho/pendência** → valida → **confirmação humana** →
  API grava. Nada lançado por "entendimento" da LLM.
- Auditoria read-only: agent API só **GET**; escopos `write:*` **sem endpoint**; **não há**
  tabela de inbox/rascunho; escrita só nas rotas humanas (JWT).
- Veredito: **aprovar com cuidado**, faseado. MVP = **inbox textual**; passo 0 = "mensagem
  p/ secretária" (zero escrita).
- Docs: `roadmap/PLANO_SECRETARIA_OPERACIONAL.md`, `arquitetura/INBOX_OPERACIONAL_DESIGN.md`,
  `seguranca/WRITE_TOOLS_GUARDRAILS.md`; checkpoint 0007. LLM/escrita **não** ativadas.

## 2026-05-31 — Planejamento da Fase 2 (LLM como seletor de tools read-only)

- **Planejamento (sem código, sem ativar LLM).** Conceito: LLM apenas interpreta a mensagem
  → escolhe **uma tool permitida** → passa args simples → recebe dados da API → **redige**.
  Nunca acessa banco/Prisma/SQL/HTTP livre, nunca executa/escreve, nunca calcula valor final.
- Comandos atuais viram **tools internas** (`consultar_*`); tools compostas futuras
  (`gerar_resumo_executivo`, `explicar_painel`, `gerar_checklist_prioridades`).
- Docs: `roadmap/PLANO_LLM_FASE_2.md`, `arquitetura/LLM_TOOLS_DESIGN.md`,
  `seguranca/LLM_GUARDRAILS.md`; checkpoint 0006. `LLM_ENABLED=false` (inalterado).

## 2026-05-31 — Deploy real na VPS via Docker Compose e operador interativo documentado

- **Agente EM PRODUÇÃO na VPS** (`root@srv822821`, `~/agentefin`) via Docker Compose
  (commit `9ca3e3e`); container `agentefin` `Up`. Easypanel descartado (limite de 3 projetos).
- Validado ao vivo no Telegram (`brglobalcontas_bot`, token+chave **rotacionados**):
  `/start` e `/painel` com **dados reais** (Vencidas 7 · R$ 19.420,23 · Conciliação 234/75).
- Evidências em `docs/operacao/evidencias-testes.md` §7; checkpoint 0005; manuais de deploy/operador atualizados.
- `LLM_ENABLED=false`, sem scheduler, sem Fase 2, sem novas funcionalidades.

## 2026-05-31 — Operador interativo da VPS (assistente de configuração)

- Novo `scripts/ops/agentefin-vps.sh`: menu (verificar ambiente, **configurar `.env`
  por assistente**, deploy/update, status, logs, restart, parar, validar `/whoami`, checklist).
- Opção 2 troca token/chave/LLM **sem editor**: backup `.env.bak.*`, segredos ocultos e
  mascarados, `chmod 600`, validações. `bash -n` OK. LLM segue **futura** (bot inalterado).
- Doc `docs/deploy/OPERADOR_VPS_INTERATIVO.md` + checkpoint 0004. Sem scheduler, sem Fase 2.

## 2026-05-31 — Preparação de deploy direto na VPS (Docker Compose)

- **Easypanel descartado** (licença gratuita limita a 3 projetos) → deploy via
  **Docker Compose direto na VPS**. Bot por polling: sem porta/domínio/proxy/SSL.
- `docker-compose.yml` ajustado (serviço `agentefin`, sem ports, sem volumes, stateless,
  rotação de logs json-file 10MB×3). Novo guia `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md`.
- Scripts `scripts/deploy/vps-docker-{deploy,status,stop}.sh`; `.gitattributes` (LF em `*.sh`).
- `docs/deploy/easypanel.md` marcado como descontinuado. Sem scheduler, sem Fase 2, sem novas funcionalidades.

## 2026-05-31 — Homologação real contra PRODUÇÃO (local)

- API Key do agente criada (id 7, `bgf_live_ecffe92489e…`, escopos `read:financeiro,read:extrato`)
  e **validada**: `/whoami` → **200** contra `https://lixo.brglobal.com.br/api/agent/v1`.
- Comandos testados com **dados reais** (batem com o cron das 05:00): `/vencidas` 7 contas
  R$ 19.420,23; `/resumo`; `/painel` (matches 234/75, sugestões 19); `/hoje`,`/criticas`,`/proximos7` vazios; `/ajuda`.
- Bot `Brglobal_financeiro_bot` em polling **localmente** (não em produção); TLS ok (AVG desligado).
- Pendência: **deploy Easypanel**. ⚠️ **Rotacionar** `TELEGRAM_BOT_TOKEN` e `BRGLOBAL_API_KEY` (expostos no chat).
- Sem push, sem deploy, sem scheduler, sem novas funcionalidades.

## 2026-05-30 — Auditoria final (correções de bugs)

- **Boot com `.env.example` as-is:** `DEFAULT_CONTA_BANCARIA_ID` vazio agora vira
  `None` (field_validator) — antes lançava `ValidationError` no import.
- **Cliente HTTP:** `404` não é mais retentado (retry só em 5xx/rede/timeout/rate-limit).
- **`AccessMiddleware`:** fallback `event.from_user` (robustez).
- +2 testes de regressão → **26 testes**. `docker build` + `docker run` (safe boot) validados.

## 2026-05-30 — Implementação inicial (MVP leitura)

- **ETAPA 0** Auditoria dos projetos de referência; resolvido o erro
  `@prisma/client did not initialize` (gerar via `pnpm run db:generate`);
  descoberta da discrepância de versão (`/api/agent/v1` só existe na base 28-05);
  decisão "não usar Hermes" materializada (bot Telegram limpo sobre `/api/agent/v1`).
  Doc: `docs/arquitetura/DECISAO_ARQUITETURAL_INICIAL.md`.
- **ETAPA 1** Estrutura documental `docs/` criada.
- **ETAPA 2** Mapa da API: `docs/arquitetura/API_BRGLOBAL.md` (endpoints +
  tabela comando→endpoint).
- **ETAPA 3/4** Implementado: `config`, `logging_setup`, `client` (HTTP robusto:
  timeout/retry/erros tipados/degradação), `formatters`, `commands` (router),
  `bot` (middleware whitelist + rate limit), `llm` (opcional, off), `main`.
  Comandos: `/hoje /vencidas /criticas /proximos7 /painel /resumo /whoami /ajuda`.
- **ETAPA 5** 24 testes (unit + integração over-the-wire) passando. Evidência real
  contra a API: `/health` 200 e contrato 401. `docs/operacao/evidencias-testes.md`.
- **ETAPA 6** Docker: `Dockerfile` (`python:3.12-slim` + tzdata, sem porta),
  `docker-compose.yml`, `.dockerignore`, `.env.example`.
- **ETAPA 7** Checkpoint inicial e `ESTADO-ATUAL`.
- **ETAPA 9** Commits locais organizados (sem push).
