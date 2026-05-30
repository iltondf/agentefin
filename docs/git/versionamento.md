# Versionamento (Git)

## Ritual obrigatório
```
implementar → testar → documentar → checkpoint → commit local
```
**Push só com autorização explícita do usuário.** Nunca push automático.

## Repositório
- Remote: `https://github.com/iltondf/agentefin.git` (origin)
- Branch: `main`

## Convenções de commit
Prefixos: `feat`, `fix`, `docs`, `test`, `chore`, `build`. Mensagens curtas e
descritivas, em português. Um commit por marco lógico.

## Nunca versionar
`.env`, `data/`, `logs/`, `_verificar_*.py`, `_*.log` (ver `.gitignore`).
Verificar antes do commit que nenhum segredo entrou.
