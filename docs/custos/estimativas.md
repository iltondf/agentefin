# Custos

## Tokens (LLM)
**Zero por padrão.** `LLM_ENABLED=false` → todos os comandos são determinísticos
(0 token). A LLM só é chamada para **texto livre** quando habilitada, e mesmo assim
sobre um contexto pequeno (resumo diário), com `max_tokens=500`.

Estimativa (se habilitada, modelo barato OpenRouter): cada pergunta livre ≈ entrada
de ~500–1500 tokens + saída ≤500. Comandos `/...` permanecem 0 token.

## Infra
- 1 container pequeno (Python slim), sem banco externo, sem porta. Custo de
  hospedagem mínimo (Easypanel/VPS).
- Tráfego: 1 chamada HTTP de saída por comando; rate-limit 60/min por chave no servidor.

## Princípio
Maximizar valor por token e por linha de código: o servidor já faz o trabalho
pesado; o agente só consulta e formata.
