"""Fluxo Telegram: criar rascunho → corrigir → confirmar (executa write) → cancelar.
Usa MockTransport (sem rede real) e store SQLite temporário."""
import httpx
import pytest
from types import SimpleNamespace

from financebot import commands, config as cfgmod
from financebot.client import FinanceClient
from financebot.drafts import DraftStore

UID = 42


class FakeMsg:
    def __init__(self, text):
        self.text = text
        self.from_user = SimpleNamespace(id=UID)
        self.chat = SimpleNamespace(id=UID)
        self.replies = []

    async def answer(self, txt):
        self.replies.append(txt)


def _store(tmp_path):
    return DraftStore(tmp_path / "f.db")


def _client(handler):
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(handler))


async def test_confirmar_executa_write(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "brglobal_write_api_key", "w")
    calls = {"post": 0}

    def h(req):
        if req.method == "GET" and "funcionarios/buscar" in str(req.url):
            return httpx.Response(200, json={"data": {"ok": True, "data": {
                "candidatos": [{"id": 10, "nome": "Edson"}], "ambiguo": False}}})
        if req.method == "POST" and "rh/lancamentos" in str(req.url):
            calls["post"] += 1
            return httpx.Response(200, json={"data": {"ok": True, "data": {
                "lancamentoId": 291, "valor": 1}, "message": "Lançamento #291 criado", "warnings": []}})
        return httpx.Response(404, json={})

    store = _store(tmp_path)
    d = store.create(chat_id=UID, user_id=UID, texto="x", dominio="rh",
                     intent="criar_lancamento_rh",
                     payload={"nomeFuncionario": "Edson", "tipo": "ajuste_positivo",
                              "destino": "pagamento", "valorUnit": 1, "qtd": 1, "data": "2026-06-21"})
    m = FakeMsg(f"confirmar {d.id}")
    await commands._maybe_pendencia_cmd(m, store, _client(h), cfgmod.settings, m.text.lower())
    assert calls["post"] == 1
    assert store.get(d.id).status == "executado"
    assert "291" in " ".join(m.replies)


async def test_confirmar_sem_write_enabled_nao_posta(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", False)
    calls = {"post": 0}

    def h(req):
        if req.method == "GET":
            return httpx.Response(200, json={"data": {"ok": True, "data": {
                "candidatos": [{"id": 10, "nome": "Edson"}], "ambiguo": False}}})
        calls["post"] += 1
        return httpx.Response(200, json={"data": {"ok": True, "data": {}}})

    store = _store(tmp_path)
    d = store.create(chat_id=UID, user_id=UID, texto="x", dominio="rh",
                     intent="criar_lancamento_rh",
                     payload={"funcionarioId": 10, "tipo": "ajuste_positivo", "destino": "pagamento",
                              "valorUnit": 1, "qtd": 1, "data": "2026-06-21"})
    m = FakeMsg(f"confirmar {d.id}")
    await commands._maybe_pendencia_cmd(m, store, _client(h), cfgmod.settings, m.text.lower())
    assert calls["post"] == 0
    assert store.get(d.id).status == "confirmado"
    assert "desabilitada" in " ".join(m.replies).lower()


async def test_confirmar_ambiguo_pergunta(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "brglobal_write_api_key", "w")

    def h(req):
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": 1, "nome": "Joao A"}, {"id": 2, "nome": "Joao B"}], "ambiguo": True}}})

    store = _store(tmp_path)
    d = store.create(chat_id=UID, user_id=UID, texto="x", dominio="rh",
                     intent="criar_lancamento_rh",
                     payload={"nomeFuncionario": "Joao", "tipo": "ajuste_positivo",
                              "destino": "pagamento", "valorUnit": 1, "qtd": 1, "data": "2026-06-21"})
    m = FakeMsg(f"confirmar {d.id}")
    await commands._maybe_pendencia_cmd(m, store, _client(h), cfgmod.settings, m.text.lower())
    assert store.get(d.id).status == "pendente"   # não executou
    assert "mais de um" in " ".join(m.replies).lower()


async def test_cancelar_nao_posta(tmp_path):
    store = _store(tmp_path)
    d = store.create(chat_id=UID, user_id=UID, texto="x", intent="criar_conta_pagar", payload={})
    m = FakeMsg(f"cancelar {d.id}")
    await commands._maybe_pendencia_cmd(m, store, None, cfgmod.settings, m.text.lower())
    assert store.get(d.id).status == "cancelado"


async def test_corrigir_atualiza_campo(tmp_path):
    store = _store(tmp_path)
    d = store.create(chat_id=UID, user_id=UID, texto="x", intent="criar_conta_pagar",
                     payload={"valor": 9})
    m = FakeMsg(f"corrigir {d.id} valor 1")
    await commands._maybe_pendencia_cmd(m, store, None, cfgmod.settings, m.text.lower())
    assert store.get(d.id).payload_extraido["valor"] == "1"


async def test_reconfirmar_executado_nao_duplica(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "brglobal_write_api_key", "w")
    store = _store(tmp_path)
    d = store.create(chat_id=UID, user_id=UID, texto="x", intent="criar_lancamento_rh", payload={})
    store.set_status(d.id, "executado")
    calls = {"post": 0}

    def h(req):
        calls["post"] += 1
        return httpx.Response(200, json={"data": {"ok": True, "data": {}}})

    m = FakeMsg(f"confirmar {d.id}")
    await commands._maybe_pendencia_cmd(m, store, _client(h), cfgmod.settings, m.text.lower())
    assert calls["post"] == 0
    assert "já foi executada" in " ".join(m.replies).lower()
