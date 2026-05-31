# Plano — Secretária Operacional (inbox + rascunhos com confirmação)

> **PLANEJAMENTO. NÃO implementado.** Nada de código/banco/migration/endpoint/deploy.
> O agente segue em produção como bot read-only determinístico (sem LLM).

## 1. Entendimento do problema
Evoluir o bot de **consulta** para uma **captura operacional** via Telegram: o admin fala
naturalmente ("anota uma diária pro Vanderli", "paguei o boleto da Condor", "comprei uma
ferramenta de R$ 35"), e o agente transforma isso em um **rascunho/pendência estruturada**,
pede **confirmação/revisão** e só então (futuro) grava no BRGlobal **via API própria**.
Nunca lançar definitivo só porque a LLM "entendeu".

## 2. O que já existe hoje (auditoria read-only do BRGlobal)
- **Agent API `/api/agent/v1`:** **9 rotas, todas GET** (read-only). **Nenhuma escrita.**
- **Escopos já definidos** (reservados, sem endpoint que os honre): `write:contas`,
  `write:despesa-paga`, `write:baixas`, `write:treinamento`, `notify:resumo`.
- **Não existe** tabela de inbox/rascunho/pendência (`agente_pendentes`/`agente_logs` da
  proposta **nunca** foram criados).
- **Escrita já existe — mas só nas rotas humanas (JWT/cookie)**, não no agente:
  `POST /api/rh/lancamentos` (+ `/lote`), CRUD funcionários/fornecedores/contas-pagar,
  `POST /api/contas-pagar/:id/baixar`, `POST /api/uploads/contas-pagar` (comprovante),
  `conciliacao-treinamento` (buscar-entidade, cadastro-rapido).
- **Buscas read** disponíveis: funcionários, fornecedores, contas-pagar (inteligência/busca),
  entidade (conciliacao-treinamento).

**Conclusão:** dá para **consultar** muita coisa já; **escrever** exigiria **novos endpoints
de agente** (Bearer+escopo) no BRGlobal — as rotas humanas não servem ao bot (auth diferente).

## 3. O que falta / simples / perigoso / mudança grande
| Item | Situação |
|---|---|
| Consultar funcionário/fornecedor/conta p/ desambiguar | **Falta expor** sob `/api/agent/v1` (existe nas rotas humanas) — **simples** |
| Inbox de pendências (CRUD textual estruturado) | **Não existe** — **simples** (1 tabela + 4 rotas agent) |
| Rascunho de lançamento RH/despesa/pagamento | **Não existe** p/ agente — **médio** |
| Confirmar rascunho → grava de verdade | **Perigoso** — exige endpoints de escrita + idempotência + auditoria |
| Baixa/pagamento real pelo bot | **Perigoso/grande** — só com dupla confirmação e endpoint dedicado |

## 4. Arquitetura mais simples (recomendada)
**Caixa de entrada (inbox) + confirmação**, em camadas, do mais barato ao mais arriscado:
```
Telegram → LLM interpreta → agente monta RASCUNHO estruturado (Python valida campos)
        → agente RESUME e pede confirmação/correção/cancelar (ou "marcar p/ revisão")
        → [só depois de confirmação humana] BRGlobal grava via API PRÓPRIA de agente
```
Nada é gravado por "entendimento" da LLM. A LLM **interpreta e pergunta**; o **agente
valida**; o **humano confirma**; a **API** grava. Ver `arquitetura/INBOX_OPERACIONAL_DESIGN.md`.

## 5. Vale criar inbox operacional? (ETAPA 2 — onde mora)
| Opção | Simplicidade | Risco | Migration | Tela BRGlobal | Recomendação |
|---|---|---|---|---|---|
| **A) Tabela inbox no BRGlobal** | média | baixo | sim (1 tabela) | desejável (revisar/confirmar) | ✅ **alvo** (persistente, auditável, secretária revisa no app) |
| B) Inbox local no agente (SQLite) | alta | médio (estado fora da fonte da verdade) | não | não | ⚠️ só protótipo |
| C) Sem inbox, só endpoints definitivos | baixa | **alto** (grava direto) | — | — | ❌ contra o princípio |
| D) Híbrido (rascunho local → confirma → grava no BRGlobal) | média | baixo | sim (escrita) | opcional | ✅ caminho de transição |

**Recomendação:** começar pela **inbox textual no BRGlobal** (A) — é a forma mais simples de
capturar sem arriscar lançamento, e a secretária revisa/classifica no app. Rascunhos por
domínio (D) vêm depois.

## 6. Vale criar rascunhos por domínio? 
Sim, **depois** da inbox. Rascunho RH/despesa/pagamento agrega valor (pré-preenche), mas
exige busca de entidade + validação + endpoint de confirmação. **Fazer por etapas**, não tudo de uma vez.

## 7. Endpoints que faltariam (ideais — ETAPA 7)
**Recomendado: começar pela inbox genérica** (menos superfície):
```
GET  /api/agent/v1/rh/funcionarios?busca=        (read:rh)          — desambiguar
GET  /api/agent/v1/fornecedores?busca=           (read:fornecedores)
GET  /api/agent/v1/contas-pagar?busca=           (read:financeiro)  — achar conta paga
POST /api/agent/v1/inbox/pendencias              (write:inbox)
GET  /api/agent/v1/inbox/pendencias[/:id]        (read:inbox)
POST /api/agent/v1/inbox/pendencias/:id/cancelar (write:inbox)
POST /api/agent/v1/inbox/pendencias/:id/confirmar (confirm:*)       — FASE posterior, grava
```
Endpoints específicos por domínio (`/rh/lancamentos/rascunho`, `/despesas/rascunho`,
`/pagamentos/rascunho`) só se a inbox genérica não bastar (evitar proliferação).

## 8. Fluxo de confirmação (resumo)
Interpretar → montar rascunho → **mostrar resumo** com opções (Criar pendência / Lançar /
Corrigir / Cancelar) → desambiguar quando houver >1 funcionário/conta → **idempotência**
(evitar duplicado) → **expiração** de rascunho não confirmado. Detalhe e exemplos em
`arquitetura/INBOX_OPERACIONAL_DESIGN.md` §Fluxos.

## 9. Como a LLM entra (ETAPA 5)
**Pode:** interpretar a frase; extrair valor/data/pessoa/fornecedor/tipo provável; sugerir
categoria; gerar pergunta de esclarecimento; resumir o rascunho. **Sempre** como seletor de
tool + extrator + redator (igual à Fase 2 LLM). Ver `seguranca/WRITE_TOOLS_GUARDRAILS.md`.

## 10. Onde a LLM é PROIBIDA
Gravar/confirmar sozinha; decidir baixa/pagamento; criar definitivo sem confirmação; escolher
funcionário/conta **ambíguo**; inventar dado; pular validação determinística; chamar endpoint
livre; receber token/chave; calcular valor financeiro final.

## 11. Riscos
Erro de nome/fornecedor parecido; valor/data ambíguos; tipo errado (vale×diária×despesa×
pagamento); **duplicidade**; categoria/centro de custo/obra errados; lançamento indevido;
custo LLM; escopo creep. Mitigação: rascunho+confirmação, desambiguação obrigatória,
idempotency-key, auditoria (origem Telegram, usuário, status), escopos separados.

## 12. MVP mais simples (ETAPA 9)
| Opção | Esforço | Risco | Valor | Impacto BRGlobal | Recomendação |
|---|---|---|---|---|---|
| **1) Inbox textual estruturada** ("anota p/ revisar") | **baixo** | **baixo** | alto | 1 tabela + 3-4 rotas agent | ✅ **MVP** |
| 2) Rascunhos por domínio (RH/despesa/pagamento) | médio-alto | médio | alto | várias rotas + buscas | depois |
| 3) Só consulta + "mensagem p/ secretária" (não grava) | mínimo | mínimo | médio | **zero** | ✅ **passo 0** imediato |
| 4) Não fazer (mudança grande) | — | — | — | — | só se inbox for vetada |

## 13. Veredito
**APROVAR COM CUIDADO** — caminho faseado:
1. **Agora (sem mexer no BRGlobal):** "mensagem para a secretária" (opção 3) — o bot resume
   o pedido e manda texto pronto; **zero escrita**. Valor imediato, risco nulo.
2. **Próximo (MVP real):** **inbox textual** no BRGlobal (opção 1) — captura estruturada com
   revisão humana no app. Esforço baixo, base para tudo.
3. **Depois:** rascunhos por domínio + confirmação que grava (escopos `write:*`/`confirm:*`,
   idempotência, auditoria).
**Não** pular direto para gravar lançamento/baixa via bot.

## 14. Fases (ETAPA 10) — só se aprovado
| Fase | Objetivo | BRGlobal | Agente | Risco | Aceite |
|---|---|---|---|---|---|
| **0** | Planejamento (esta) | — | docs | baixo | docs aprovadas |
| **1** | "Mensagem p/ secretária" (sem gravar) | — | tool/redação | baixo | bot resume pedido em texto pronto |
| **2** | **Inbox** genérica de pendências | 1 tabela + rotas agent (`write:inbox`/`read:inbox`) | tools inbox | médio | criar/listar/cancelar pendência; revisão no app |
| **3** | Busca funcionário/fornecedor/conta (desambiguação) | expor `GET` sob agent | tools busca | médio | desambigua antes de propor |
| **4** | Rascunhos por domínio + **confirmação que grava** | endpoints escrita + `confirm:*` + idempotência + auditoria | rascunho+confirmação | **alto** | grava só após confirmação; sem duplicado |
| **5** | Anexos/fotos/comprovantes | upload agent | envio de foto | médio | comprovante anexado ao rascunho |
| **6** | Automações | — | — | — | só após maturidade |

## Relacionados
- `docs/arquitetura/INBOX_OPERACIONAL_DESIGN.md` (modelo de dados, fluxos, tools)
- `docs/seguranca/WRITE_TOOLS_GUARDRAILS.md` (guardrails de escrita)
- `docs/roadmap/PLANO_LLM_FASE_2.md` (LLM como seletor de tools — base para isto)
