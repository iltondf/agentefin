"""Defaults simples (YAML), sem segredo. Carregamento tolerante a ausência.

Usado para minimizar perguntas: obra padrão, conta bancária padrão, categoria por
palavra, diária padrão por funcionário, destino RH padrão, forma de pagamento padrão.
Regra: quando um default é usado, o agente DEVE mostrar no resumo.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_cache: dict | None = None


def _parse_yaml(text: str) -> dict:
    """Parser YAML mínimo (sem dependência). Suporta o subconjunto do defaults.yaml:
    mapeamentos aninhados por indentação de 2 espaços e valores escalares.
    Para casos mais ricos, instalar pyyaml — mas mantemos simples e sem dep nova."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except Exception:
        pass
    # fallback bem simples (chave: valor / aninhamento por indentação)
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, _, val = raw.strip().partition(":")
        key = key.strip()
        val = val.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce(val)
    return root


def _coerce(v: str) -> Any:
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if v.isdigit():
        return int(v)
    return v.strip('"').strip("'")


def load_defaults(path: str | Path) -> dict:
    global _cache
    p = Path(path)
    if not p.exists():
        _cache = {}
        return _cache
    try:
        _cache = _parse_yaml(p.read_text(encoding="utf-8")) or {}
    except OSError:
        _cache = {}
    return _cache


def get(path: str, default: Any = None) -> Any:
    """Acesso por caminho pontilhado: get('rh.destinoPadrao')."""
    node: Any = _cache or {}
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node


def categoria_por_palavra(texto: str) -> int | None:
    """Sugere categoriaId por palavra-chave no texto (areia/material/ferramenta...)."""
    cats = (get("categorias") or {})
    low = (texto or "").lower()
    for palavra, cat_id in cats.items():
        if palavra.lower() in low and isinstance(cat_id, int):
            return cat_id
    return None


def _norm_alias(s: str) -> str:
    """Normaliza um alias de conta: minúsculas, sem espaços/acentos básicos."""
    return (str(s or "")).lower().replace(" ", "").replace("ç", "c")


def conta_por_alias(alias: str) -> int | None:
    """Resolve contaBancariaId por alias configurado em defaults `contasBancarias`.
    Aceita 'conta1', 'conta um', 'contaUm', 'final85', '85'... (normalizado)."""
    mapa = (get("contasBancarias") or {})
    if not mapa or not alias:
        return None
    alvo = _norm_alias(alias)
    for chave, cid in mapa.items():
        if _norm_alias(chave) == alvo and isinstance(cid, int):
            return cid
    return None


def conta_por_final(final: str) -> int | None:
    """Resolve por final via mapa `contasBancarias` (chave 'final85'/'85') — comparação flexível."""
    if not final:
        return None
    digs = "".join(ch for ch in str(final) if ch.isdigit()).lstrip("0") or "0"
    mapa = (get("contasBancarias") or {})
    for chave, cid in mapa.items():
        k = _norm_alias(chave)
        kd = "".join(ch for ch in k if ch.isdigit()).lstrip("0") or "0"
        if (k in (f"final{digs}", digs) or kd == digs) and isinstance(cid, int):
            return cid
    return None
