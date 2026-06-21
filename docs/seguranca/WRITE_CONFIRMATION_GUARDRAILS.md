# Guardrails de ESCRITA + confirmação — obrigatórios (planejamento)

Fonte: spec agent-ready (raiz). Valem desde o 1º dia de qualquer tool de escrita.

## Fluxo inviolável
```
Telegram → LLM interpreta → rascunho → valida (determinístico) → [ambíguo/falta → PERGUNTA]
        → resumo → CONFIRMAÇÃO HUMANA explícita → POST (Idempotency-Key) → API grava+audita → resultado
```
**Proibido:** `mensagem → LLM entendeu → POST`. Sem confirmação, não grava.

## Regras de POST
- **Só após confirmação humana explícita** (`confirmar N`/`confirmar tudo`).
- **Todo POST com `Idempotency-Key`**, gerada **por ação confirmada** (estável no retry):
  `tg:<chat_id>:<message_id>:<acao>:<yyyymmddHHMM>`. **Retry só com a MESMA key** (429/503/504/rede).
- Rate POST **20/min** — serializar/agrupar confirmações.
- Nunca a chave no prompt da LLM nem em log (no máximo prefixo).

## Desambiguação obrigatória
`ambiguo=true`/`candidatos>1` → **perguntar qual**. Pagamento de serviço: resolver
**terceirizado → serviço aberto → conta bancária** antes de pagar. LLM nunca escolhe sozinha.

## Mapa de erros (errorCode/HTTP → ação ao usuário)
| Código | Ação |
|---|---|
| `AMBIGUO` (422) | listar `candidatos` e perguntar qual; manter rascunho |
| `NAO_ENCONTRADO` (404) | pedir mais dados (nome completo); manter rascunho |
| `FALTA_CONTA_ORIGEM` (422) | perguntar a conta bancária; manter rascunho |
| `FALTA_FORMA_PAGAMENTO` (422) | perguntar forma (pix/transf/dinheiro/outro) |
| `DUPLICADO_PROVAVEL` (409) | mostrar o existente; confirmar → reenviar `confirmarDuplicado:true` (mesma Idem-Key? não — payload muda → nova key) |
| `EXCEDE_VALOR_COMBINADO` (422,`precisaConfirmar`) | confirmar excedente + motivo → `excedenteAutorizado:true`+`motivoExcedente` |
| `SERVICO_FINALIZADO` (422) | orientar reabrir no web; cancelar/segurar rascunho |
| `SEM_PERMISSAO` (403) | informar que a chave não tem o escopo; **não** retentar |
| `VALIDACAO` (422) | corrigir `camposFaltando`; manter rascunho |
| `IDEMPOTENCY_CONFLICT` (409) | payload mudou na mesma key → gerar **nova** key ou revisar |
| `NAO_IMPLEMENTADO` (501) | orientar usar o sistema web (ex.: fechamento→CP) |
| `401` | parar; alertar chave inválida (não logar a chave) |
| `429` | aguardar + backoff; repetir |
| `503` (kill-switch) | informar indisponibilidade temporária |
| `504` | repetir **1x** (POST só com a mesma Idem-Key) |
| `5xx` | informar falha; **não** reenviar POST sem mesma Idem-Key |

**Regra de ouro:** nunca esconder o erro do usuário; **em dúvida, não gravar**.

## Defaults com transparência
Default usado (obra/categoria/conta/forma) **aparece no resumo** ("Usei obra padrão: Rio de
Janeiro"). Campo crítico ausente sem default confiável → **perguntar**.

## Proibições (a escrita NUNCA)
inventa fornecedor/funcionário/obra/conta · grava sem confirmação · baixa conta errada · usa
chave read-only para write · repete POST sem Idem-Key · oculta erro · transforma dúvida em gravação ·
toca banco/Prisma/SQL/rotas humanas · coloca segredo no prompt.

## Chaves
Read-only (atual) **não** recebe write. Escrita usa **chave nova com escopos write** (criada de
forma controlada pelo dono do financeiro). Validar com `/whoami`. Ver `PLANO_AGENT_READY_FASE_WRITE.md` §11.
