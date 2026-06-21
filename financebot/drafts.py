"""Rascunhos/pendências persistentes (SQLite local em DATA_DIR).

Captura durante o dia → confirmação depois → POST só na confirmação (write tools).
O rascunho pode existir sem escrever no BRGlobal. NUNCA guarda segredo/chave.

Estados: pendente | aguardando_confirmacao | confirmado | cancelado | executado | erro
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fin_draft (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    texto_original TEXT NOT NULL DEFAULT '',
    dominio TEXT NOT NULL DEFAULT 'indefinido',
    intent TEXT,
    payload_extraido TEXT NOT NULL DEFAULT '{}',
    campos_faltando TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pendente',
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    expires_at TEXT,
    idempotency_key TEXT,
    resultado_api TEXT,
    erro_api TEXT
);
CREATE INDEX IF NOT EXISTS idx_draft_user_status ON fin_draft(user_id, status);
"""

ATIVOS = ("pendente", "aguardando_confirmacao", "confirmado", "erro")


@dataclass
class Draft:
    id: int
    chat_id: int
    user_id: int
    texto_original: str
    dominio: str
    intent: str | None
    payload_extraido: dict
    campos_faltando: list
    status: str
    criado_em: str
    atualizado_em: str
    expires_at: str | None
    idempotency_key: str | None
    resultado_api: dict | None
    erro_api: str | None


class DraftStore:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.available = False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._conn() as c:
                c.executescript(_SCHEMA)
            self.available = True
        except sqlite3.Error:
            self.available = False  # sem persistência → caller avisa o usuário

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _row(self, r: sqlite3.Row) -> Draft:
        return Draft(
            id=r["id"], chat_id=r["chat_id"], user_id=r["user_id"],
            texto_original=r["texto_original"], dominio=r["dominio"], intent=r["intent"],
            payload_extraido=json.loads(r["payload_extraido"] or "{}"),
            campos_faltando=json.loads(r["campos_faltando"] or "[]"),
            status=r["status"], criado_em=r["criado_em"], atualizado_em=r["atualizado_em"],
            expires_at=r["expires_at"], idempotency_key=r["idempotency_key"],
            resultado_api=json.loads(r["resultado_api"]) if r["resultado_api"] else None,
            erro_api=r["erro_api"],
        )

    def create(self, *, chat_id: int, user_id: int, texto: str, dominio: str = "indefinido",
               intent: str | None = None, payload: dict | None = None,
               faltando: list | None = None, ttl_horas: int = 48) -> Draft:
        now = self._now()
        exp = (datetime.now(timezone.utc) + timedelta(hours=ttl_horas)).isoformat()
        status = "aguardando_confirmacao" if not (faltando or []) else "pendente"
        with self._conn() as c:
            cur = c.execute(
                """INSERT INTO fin_draft
                   (chat_id,user_id,texto_original,dominio,intent,payload_extraido,
                    campos_faltando,status,criado_em,atualizado_em,expires_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (chat_id, user_id, texto, dominio, intent,
                 json.dumps(payload or {}), json.dumps(faltando or []),
                 status, now, now, exp),
            )
            new_id = cur.lastrowid
        return self.get(new_id)

    def get(self, draft_id: int) -> Draft | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM fin_draft WHERE id=?", (draft_id,)).fetchone()
        return self._row(r) if r else None

    def list_active(self, user_id: int) -> list[Draft]:
        with self._conn() as c:
            rows = c.execute(
                f"SELECT * FROM fin_draft WHERE user_id=? AND status IN ({','.join('?'*len(ATIVOS))}) ORDER BY id",
                (user_id, *ATIVOS),
            ).fetchall()
        return [self._row(r) for r in rows]

    def update(self, draft_id: int, **fields: Any) -> Draft | None:
        if not fields:
            return self.get(draft_id)
        cols, vals = [], []
        for k, v in fields.items():
            if k in ("payload_extraido", "campos_faltando", "resultado_api"):
                v = json.dumps(v)
            cols.append(f"{k}=?")
            vals.append(v)
        cols.append("atualizado_em=?")
        vals.append(self._now())
        vals.append(draft_id)
        with self._conn() as c:
            c.execute(f"UPDATE fin_draft SET {','.join(cols)} WHERE id=?", vals)
        return self.get(draft_id)

    def set_status(self, draft_id: int, status: str) -> Draft | None:
        return self.update(draft_id, status=status)

    def expire_old(self) -> int:
        """Marca como cancelado rascunhos vencidos (expires_at < agora)."""
        now = self._now()
        with self._conn() as c:
            cur = c.execute(
                "UPDATE fin_draft SET status='cancelado', atualizado_em=? "
                "WHERE expires_at IS NOT NULL AND expires_at < ? AND status IN ('pendente','aguardando_confirmacao')",
                (now, now),
            )
            return cur.rowcount
