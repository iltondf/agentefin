# Plano — Fase 2: LLM como SELETOR DE TOOLS (read-only)

> **Planejamento. NÃO implementado.** O agente segue em produção no MVP determinístico
> (sem LLM). Este documento define como introduzir LLM **com segurança** numa fase futura.

## Princípio central
A LLM **não** é o cérebro nem acessa nada diretamente. Ela é um **seletor de tools** +
**redator**. Os comandos atuais (`/hoje`, `/vencidas`, …) viram **tools internas**; a LLM
apenas escolhe **uma** tool permitida, passa **args simples** e **redige** a resposta a
partir dos dados que a tool retornou da API. A **API BRGlobal continua a fonte da verdade**.

> Determinístico-primeiro / 0-token-first: comandos conhecidos respondem **sem LLM**.
> `LLM_ENABLED=false` mantém **exatamente** o comportamento atual.

## 1. Como os comandos atuais viram tools
Cada comando passa a ter uma **tool interna** correspondente (mesma lógica que o handler
já usa: chama o cliente HTTP + formata). Comando e LLM despacham para a **mesma** tool:

| Tool | Comando atual | Endpoint (read-only) | Args | LLM p/ redigir? | Tipo |
|---|---|---|---|---|---|
| `consultar_whoami` | `/whoami` | `GET /whoami` | — | não (texto fixo) | simples |
| `consultar_hoje` | `/hoje` | `GET /contas-pagar/hoje` | — | opcional | simples |
| `consultar_vencidas` | `/vencidas` | `GET /contas-pagar/vencidas` | — | opcional | simples |
| `consultar_criticas` | `/criticas` | `GET /contas-pagar/criticas` | — | opcional | simples |
| `consultar_proximos7` | `/proximos7` | `GET /contas-pagar/proximos-dias` | `dias` (int 1–90, def. 7) | opcional | simples |
| `consultar_resumo` | `/resumo` | `GET /resumo-diario` | — | opcional | simples |
| `consultar_painel` | `/painel` | `GET /painel-operacional` | `contaBancariaId?`, `mes?` | opcional | simples |
| `gerar_resumo_executivo` | — (novo) | resumo + vencidas + criticas | — | **sim** | composta |
| `explicar_painel` | — (novo) | painel | — | **sim** | composta |
| `gerar_checklist_prioridades` | — (novo) | vencidas + criticas + resumo | — | **sim** | composta |

- **Simples:** já funcionam hoje como comando (0 token). Com LLM, servem para responder a
  **pergunta livre** equivalente ("o que está vencido?" → `consultar_vencidas`).
- **Compostas:** combinam tools simples e **exigem** a LLM só para **redigir** (nunca para calcular).

## 2. Como a LLM escolhe uma tool
1. O **router determinístico** tenta primeiro: se a mensagem é um comando conhecido
   (`/hoje`…) **ou** casa um padrão óbvio (regex curto), executa a tool **sem LLM**.
2. Só se **não** casar **e** `LLM_ENABLED=true`: a LLM recebe a lista de **tools permitidas**
   (nome + descrição + schema de args) e a mensagem do usuário, e devolve **uma** escolha:
   `{tool, args}` (via function-calling ou JSON estrito).
3. O agente **valida** a escolha contra a **whitelist** de tools; tool desconhecida ou args
   inválidos → rejeitado (fallback). A LLM **nunca** monta URL/SQL nem chama HTTP livre.

## 3. Como o agente executa a tool
O **agente** (código Python), não a LLM, executa a tool: ela chama o **endpoint
permitido** com o **Bearer** (a chave fica no agente, **nunca** na LLM), recebe o JSON real
e devolve um resultado estruturado. Args são **validados/clampados** (ex.: `dias` 1–90).

## 4. Como a resposta é redigida
- Tool simples + pergunta livre: a LLM **redige** uma resposta curta a partir **somente**
  do payload retornado (anti-invenção de valores). Sem LLM, usa o formatter determinístico.
- Tool composta: a LLM resume/explica/checklist **sobre os dados** das tools, sem recalcular.
- Fluxo (espelha o pipeline do ecossistema): `intent determinístico` → senão `LLM#1 escolhe
  tool` → `executa tool (API, Python)` → `LLM#2 redige` → degrada para texto cru/ajuda se a LLM cair.

## 5. Fallback sem LLM (obrigatório)
- `LLM_ENABLED=false` (padrão): comportamento atual intacto; pergunta livre → "use /ajuda".
- LLM ligada mas **falha/timeout**: responder com **ajuda/comandos** ou o texto determinístico
  da última tool — **nunca derrubar o bot**.
- Tool escolhida inválida / args inválidos: rejeitar e cair no fallback.

## 6. Configuração (valores seguros — sem segredo real)
```
LLM_ENABLED=false              # padrão; liga a camada LLM
LLM_PROVIDER=openrouter
LLM_MODEL=<modelo barato>      # ex.: deepseek/deepseek-chat (validar custo)
OPENROUTER_API_KEY=<só se LLM_ENABLED=true>
# parâmetros sugeridos (constantes no código):
#   timeout: 20s · max_tokens: ~500 · temperature: 0.2 · 1 retry
```
**Reconciliação (tarefa de 2.2):** hoje `core`/`config` lê `LLM_BASE_URL`/`LLM_API_KEY`;
o operador grava `LLM_PROVIDER`/`OPENROUTER_API_KEY`. A implementação deve mapear
`provider=openrouter` → base_url + usar `OPENROUTER_API_KEY` (ou aliasar para `LLM_API_KEY`).
**Fallback de provedor:** se OpenRouter cair → degradar (não trocar de provedor automaticamente).

## 7. Custo e observabilidade
- **Determinístico-primeiro** = a maioria das interações continua **0 token**.
- Logar **uso** da LLM em metadados (`llm_call tool=… ms=… tokens_in/out=… status=…`),
  **nunca** o conteúdo financeiro nem token/chave.
- **Rate limit** por usuário/min (reusar o do middleware) + contagem de chamadas.
- **Resumir/limitar o payload** antes de enviar à LLM (ex.: top-N itens), nunca payload gigante.
- **Sem memória longa**: no máximo contexto curto (Fase 2.4), poucos turnos, em memória, não persistido.

## 8. Plano por fases (pequeno)
| Fase | Objetivo | Arquivos prováveis | Risco | Aceite |
|---|---|---|---|---|
| **2.0** | Planejamento/documentação (esta) | `docs/**` | baixo | docs aprovadas; nada no código |
| **2.1** | **Registry de tools interno** (comandos passam a despachar p/ tools; **sem LLM**) | `financebot/tools.py` (novo), `commands.py` (refactor) | médio (refactor) | comandos idênticos; 26+ testes verdes; `LLM_ENABLED` irrelevante |
| **2.2** | **LLM seletor** p/ pergunta livre (tools simples) | `financebot/llm.py`, `commands.py`, `config.py` (reconciliar vars) | médio (alucinação, custo) | LLM off = comportamento atual; on = pergunta livre respondida com dado real; falha → fallback |
| **2.3** | Tools **compostas** (resumo executivo, explicar painel, checklist) | `tools.py`, `llm.py` (prompts) | médio | resume/explica sobre dado real, sem inventar valores |
| **2.4** | Contexto **curto** de conversa (perguntas de continuação) | `commands.py`, `bot.py` | médio (contexto) | "e desses, quais críticos?" funciona; memória limitada; sem persistência |

## 9. Riscos (resumo)
Alucinação de valores · prompt-injection via payload · vazamento de chave · custo/latência ·
classificação errada de tool · payload gigante · escopo creep (LLM querer "agir"). Mitigações
detalhadas em `docs/seguranca/LLM_GUARDRAILS.md`.

## Relacionados
- Arquitetura/contrato de tools + prompt: `docs/arquitetura/LLM_TOOLS_DESIGN.md`.
- Guardrails de segurança: `docs/seguranca/LLM_GUARDRAILS.md`.
