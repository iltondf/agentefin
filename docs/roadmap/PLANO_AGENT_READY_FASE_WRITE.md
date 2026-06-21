# Plano — Agent-Ready: tools de escrita com rascunhos e confirmação

> **PLANEJAMENTO. NÃO implementar.** Fonte da verdade: `BRGLOBAL_FINANCEIRO_API_AGENT_READY_2026-06-21.md`
> (raiz). O agente segue em produção read-only; nada de código/.env/deploy/LLM/POST agora.
> Refina e **supera** os planos `PLANO_LLM_FASE_2.md` e `PLANO_SECRETARIA_OPERACIONAL.md` com a API real.

## 1. Recomendação: UM bot ou VÁRIOS?
**Veredito: UM único bot com modos/módulos internos** (RH, Contas a Pagar, Terceirizados,
Consultas, Pendências). É a opção mais simples e a recomendada.

| Critério | 1 bot (modos) ✅ | 2 bots | N bots |
|---|---|---|---|
| Simplicidade / deploy | 1 container, 1 token, 1 `.env` | 2× tudo | N× tudo |
| Manutenção / logs | centralizados | duplicados | espalhados |
| UX | uma conversa; o usuário não decide "qual bot" | precisa lembrar o bot certo | confuso |
| Permissões | 1 chave write (escopos certos) | dá p/ separar read/write | superfície maior |
| Risco de confusão | baixo (LLM roteia por intent) | médio | alto |
| Custo operacional | menor | maior | maior |

**Quando separaria:** só se um domínio exigir **chave/escopo isolado por compliance**, equipes
distintas, ou volume que justifique escalar um módulo sozinho. Não é o caso hoje.

## 2. Arquitetura geral
```
Telegram → router determinístico (comandos antigos = 0 token, intactos)
        → senão, se LLM_ENABLED: LLM PARSER → JSON {intent, fields, missing, shouldAsk}
        → agente monta RASCUNHO → resolve IDs via GET (busca) → valida (schema/determinístico)
        → se ambíguo/falta campo: PERGUNTA o mínimo  |  senão: guarda rascunho
        → usuário CONFIRMA explicitamente
        → tool de ESCRITA: POST /api/agent/v1/... com Idempotency-Key
        → API grava + audita → agente mostra resultado (id, saldo, etc.)
```
- **Comando manual e LLM chamam a MESMA camada de tools** (a LLM é seletor, não executor).
- **A API é a fonte da verdade**: categoria/obra/saldo/baixa/idempotência/auditoria são do servidor.

## 3. Como usar a API nova (essencial)
- Base `https://lixo.brglobal.com.br/api/agent/v1`; `Authorization: Bearer <env>`.
- **Envelope:** antigos → `envelope.data` (cru); **novos → `envelope.data.data`** (recurso) e
  erro em `envelope.error = {ok:false, errorCode, precisaConfirmar, message, candidatos, camposFaltando}`.
  → o **cliente HTTP precisa de 2 modos de unwrap** (ver `AGENT_READY_TOOLS_WRITE_DESIGN.md`).
- **Rate limit:** 60/min GET, **20/min POST**. **Timeout** ~30–35s. **Retry** só 429/503/504/rede;
  **POST só re-tentado com a MESMA `Idempotency-Key`**.
- **Escopos:** leitura `read:financeiro|extrato|rh|terceirizados|cadastros`; escrita
  `write:financeiro|rh|terceirizados|cadastros_basico`. (⚠️ **não existe `read:fornecedores`** — usa `read:financeiro`.)

## 4. Tools de leitura novas
Detalhe (endpoint/escopo/args/exemplo/risco) em `AGENT_READY_TOOLS_WRITE_DESIGN.md` §Read.
Resumo: `buscar_funcionarios`, `buscar_fornecedores`, `buscar_obras`, `buscar_unidades`,
`buscar_terceirizados`, `buscar_servicos_terceirizado`, `detalhar_servico_terceirizado`,
`buscar_contas_bancarias`, `consultar_fechamento_rh`, `consultar_resumo_rh`,
`consultar_extrato_rh`, `buscar_pix`, `buscar_extrato`, `buscar_contas_pagar`. Todas **read**,
sem confirmação, servem para **resolver IDs** antes de escrever.

## 5. Tools de escrita planejadas (NÃO implementar)
6 tools, todas com **confirmação humana + Idempotency-Key**. Payloads e regras completas em
`AGENT_READY_TOOLS_WRITE_DESIGN.md` §Write:
1. `criar_lancamento_rh` → `POST /rh/lancamentos` (write:rh)
2. `criar_conta_pagar` → `POST /financeiro/contas-pagar` `pago:false` (write:financeiro)
3. `criar_conta_pagar_paga` → idem `pago:true` (+conta/forma/data)
4. `registrar_pagamento_servico_terceirizado` → `POST /terceirizados/servicos/:id/pagamentos` (write:terceirizados)
5. `criar_servico_terceirizado` → `POST /terceirizados/servicos` (write:terceirizados)
6. `cadastrar_terceirizado` → `POST /terceirizados` (write:terceirizados|cadastros_basico)
> **Bloqueado:** `POST /rh/fechamento/conta-pagar` → **501 NAO_IMPLEMENTADO** (fica no web). Não planejar.

## 6. Rascunhos / pendências
Ver `RASCUNHOS_PENDENCIAS_DESIGN.md`. **Recomendação: SQLite local no agente, em volume
persistente** (`/app/data`) — não há endpoint de inbox no BRGlobal. Captura durante o dia;
confirmação depois; POST só na confirmação.

## 7. Confirmação
Sempre: montar resumo legível → usuário responde `confirmar N` / `confirmar tudo` /
`cancelar N` / `corrigir N`. Guardrails em `WRITE_CONFIRMATION_GUARDRAILS.md`.

## 8. Como a LLM interpreta
LLM = **parser** que devolve **JSON estruturado** (`{intent, confidence, fields, missing,
shouldAsk, question}`), nunca texto livre, nunca POST, nunca escolhe ambíguo, nunca inventa ID.
IDs vêm das tools de busca. Detalhe em `LLM_PARSER_GUARDRAILS.md`.

## 9. Defaults e aprendizado simples
**Recomendação: arquivo de config (YAML/JSON) versionável no agente + overrides em SQLite**
(aprendizado leve por uso). Sem IA. Ex.: obra padrão, conta bancária padrão, categoria por
palavra (areia/material/ferramenta), diária padrão por funcionário, destino RH padrão, forma
de pagamento padrão = pix. **Regra:** usar default com confiança alta **mostrando no resumo**
("Usei obra padrão: Rio de Janeiro"); faltando campo crítico → perguntar. Detalhe no design de tools.

## 10. Tratamento de erros
Mapa completo (errorCode/HTTP → ação) em `WRITE_CONFIRMATION_GUARDRAILS.md` §Erros, cobrindo
AMBIGUO, NAO_ENCONTRADO, FALTA_CONTA_ORIGEM, FALTA_FORMA_PAGAMENTO, DUPLICADO_PROVAVEL,
EXCEDE_VALOR_COMBINADO, SERVICO_FINALIZADO, SEM_PERMISSAO, VALIDACAO, IDEMPOTENCY_CONFLICT,
NAO_IMPLEMENTADO, 401/403/404/429/503/504/5xx. Regra de ouro: **nunca esconder erro; em dúvida, não gravar.**

## 11. Escopos / chaves
**Recomendação: DUAS chaves.** (a) a **read-only atual** (intacta) para consultas; (b) uma
**chave nova com escopos write** (`write:financeiro,write:rh,write:terceirizados,
write:cadastros_basico` + os `read:*` necessários p/ resolver IDs). Justificativa: a read-only
**não** deve ganhar write (regra §4.3 do doc); separar limita o estrago se a chave de consulta
vazar; o operador VPS já sabe trocar chave (opção 2 do menu). Validar ambas com `/whoami`.
*(Alternativa "1 chave read+write" é mais simples mas concentra risco — não recomendada.)*

## 12. Fases de implementação
| Fase | Objetivo | Arquivos prováveis | Risco | Sobe em prod? | Aceite |
|---|---|---|---|---|---|
| **0** | Planejamento/doc (esta) | `docs/**` + spec na raiz | baixo | n/a | docs aprovadas |
| **1** | Cliente HTTP 2-envelopes + **registry de tools READ novas** | `client.py`, `tools.py` (novo), `commands.py` | médio | sim (read) | GETs novos funcionam; comandos antigos intactos |
| **2** | **Rascunhos locais** (SQLite em `/app/data`) + comandos `pendências/confirmar/cancelar` | `drafts.py` (novo), `commands.py`, `docker-compose.yml` (volume) | médio | sim (sem write) | criar/listar/cancelar rascunho; persiste em redeploy |
| **3** | **LLM parser** (JSON) sem escrita | `llm.py`, `parser.py` (novo) | médio | sim (LLM opcional, default off) | LLM off = igual hoje; on = gera rascunho |
| **4** | **RH:** `criar_lancamento_rh` c/ confirmação + Idempotency | `tools_write.py`, `commands.py` | **alto** | só após teste controlado | grava após confirmar; replay não duplica |
| **5** | **Financeiro:** `criar_conta_pagar[_paga]` | `tools_write.py` | **alto** | idem | idem + obra/categoria/forma validadas |
| **6** | **Terceirizados:** pagamento serviço + criar serviço + cadastrar | `tools_write.py` | **alto** | idem | resolve terceirizado→serviço; saldo correto |
| **7** | **Defaults/aprendizado simples** | `defaults.yaml`, `defaults.py` | médio | sim | default mostrado no resumo |
| **8** | **Resumo de pendências no fim do dia** | `commands.py` (+ scheduler? decisão à parte) | médio | sim | "você tem N pendências" |
| **9** | Hardening/refino | vários | médio | sim | testes completos verdes |

> Fases 4–6 (escrita) **só sobem após** teste em ambiente controlado/mock e **autorização explícita**
> para o 1º POST real (com marcador de teste + limpeza).

## 13. Riscos
Escrita indevida (mitigado: confirmação + idempotência) · ambiguidade de nome/conta · perda de
rascunho se faltar volume · custo/latência LLM · 2 envelopes (parsing) · rate limit POST 20/min ·
chave write vazar · divergência entre captura e estado real no BRGlobal entre captura e confirmação.

## 14. O que é simples
Tools READ novas (espelham GETs); rascunho SQLite; comandos de confirmação; defaults em YAML;
tratamento de erro (mapa pronto). Reusa todo o padrão atual do agente.

## 15. O que é complexo
LLM parser confiável (PT, valores/datas) · resolução multi-passo (terceirizado→serviço→conta) ·
idempotência correta por ação · UX de confirmação de múltiplos itens · manter comandos antigos intactos.

## 16. O que NÃO fazer agora
Não implementar; não POST em produção; não ativar LLM; não criar chave write ainda; não migration;
não tocar no financeiro; não planejar fechamento→CP (501). **Não** dar à chave read-only escopo write.

## Documentos relacionados
`AGENT_READY_TOOLS_WRITE_DESIGN.md` · `RASCUNHOS_PENDENCIAS_DESIGN.md` ·
`WRITE_CONFIRMATION_GUARDRAILS.md` · `LLM_PARSER_GUARDRAILS.md` · spec na raiz.
