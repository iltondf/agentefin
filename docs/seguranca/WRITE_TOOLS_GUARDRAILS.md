# Guardrails de ESCRITA (secretária operacional) — obrigatórios

> Planejamento. Valem desde o 1º dia de qualquer tool que **capture** ou **grave**.
> Enquanto não implementado, servem de barreira de design.

## Papel da LLM
**Pode:** interpretar frase natural; extrair valor/data/fornecedor/funcionário/tipo provável;
sugerir categoria provável; gerar pergunta de esclarecimento; **resumir o rascunho** para confirmação.

**NÃO pode:** gravar sozinha; confirmar sozinha; decidir baixa/pagamento; criar despesa/
lançamento definitivo sem confirmação; escolher funcionário/conta **ambíguo**; inventar dado;
ignorar validação determinística; chamar endpoint livre; receber token/chave; calcular valor final.

## Regra de ouro
**Interpretar ≠ executar.** A LLM produz um **rascunho**; o **código** valida; o **humano**
confirma; a **API** grava. Nenhuma escrita acontece "porque a LLM entendeu".

## Toda escrita futura exige
- **Confirmação humana explícita** (ação separada, não embutida na interpretação).
- **Idempotency-Key** (anti-duplicidade) em toda gravação.
- **Auditoria:** origem (`telegram`), `usuario_solicitante`, `status`, timestamps.
- **Endpoint próprio de agente** (Bearer + escopo de escrita) — **nunca** rota humana/JWT,
  **nunca** banco/Prisma/SQL direto.
- **Escopo dedicado** (`write:*`/`confirm:*`); a **chave read-only atual não escreve**.
- **Possibilidade de cancelar/revisar**; **expiração** de rascunho não confirmado.

## Desambiguação obrigatória
>1 funcionário/fornecedor/conta → **listar e perguntar**; a LLM **não** escolhe sozinha.
Sem correspondência → vira **pendência** (não inventa cadastro).

## Validações determinísticas (fora da LLM)
Usuário autorizado · valor>0 · data válida · funcionário ativo · fornecedor/categoria/conta
existem **ou** pendência · tipo permitido · schema do payload · logs sem segredo.

## Proibições absolutas
LLM nunca: toca banco/Prisma/SQL · monta URL/HTTP livre · recebe token/chave · executa baixa/
pagamento/conciliação/treinamento · grava definitivo sem confirmação · escolhe item ambíguo ·
inventa dado · calcula valor financeiro final.

## Fonte da verdade
A **API BRGlobal** grava e valida o lançamento definitivo. O agente é **captura + conferência**;
a LLM é **interpretação + redação**. Em dúvida: **cria pendência**, não grava.
