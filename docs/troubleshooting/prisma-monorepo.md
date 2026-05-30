# Troubleshooting — Prisma no monorepo do financeiro

> Aplica-se ao **projeto financeiro** (referência, read-only). Necessário só se
> você for subir a API local para testes. Nenhuma migration/seed é executada.

## Sintoma
- `@prisma/client did not initialize yet`
- `prisma command not found` ao rodar `pnpm prisma generate` / `pnpm exec prisma generate`

## Causa
1. O **Prisma Client nunca foi gerado** (falta o artefato de `@prisma/client`).
2. O binário `prisma` está em `packages/database/node_modules/.bin`, **não** na raiz.
   Rodar `prisma`/`pnpm exec prisma` a partir da raiz não encontra o binário.

## Solução (correta)
Gerar pelo script do workspace, que roda no pacote certo:
```powershell
pnpm run db:generate
# equivalente: pnpm --filter database generate  (→ prisma generate)
```
Esperado: `✔ Generated Prisma Client (v5.22.0)`.

## Subir a API local (read-only) para testes
```powershell
pnpm --filter api dev      # sobe Fastify (porta do .env, ex.: 3333)
# porta alternativa: $env:PORT='3334'; pnpm --filter api dev
```
Validar: `GET http://localhost:3333/health` → `{"status":"ok","db":"ok"}`.

## Pré-requisitos
- MySQL (WAMP) ativo em `:3306`, banco do `DATABASE_URL` (`brglobal_financeiro`).
- Node ≥ 20, pnpm ≥ 9 (testado: Node 22 / pnpm 10).

## NÃO fazer (BRGlobal é read-only)
`prisma migrate`, `prisma db push`, `seed`, INSERT/UPDATE/DELETE/DROP/ALTER. Gerar a
API Key do agente (`pnpm agente:create-key`) é INSERT — feito pelo **operador**, não
nesta automação.
