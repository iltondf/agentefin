"""Confirmação/cancelamento natural (sem número) + resolução com categoriaPalavra/defaults."""
import httpx
import pytest
from types import SimpleNamespace

from financebot import commands, config as cfgmod, defaults, resolve
from financebot.client import FinanceClient
from financebot.drafts import DraftStore

UID = 7


class FakeMsg:
    def __init__(self, text):
        self.text = text
        self.from_user = SimpleNamespace(id=UID)
        self.chat = SimpleNamespace(id=UID)
        self.replies = []

    async def answer(self, txt):
        self.replies.append(txt)


def _client(handler):
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(handler))


def _ok_post(req):
    if req.method == "GET":
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": 34, "nome": "Condor"}], "ambiguo": False}}})
    return httpx.Response(200, json={"data": {"ok": True, "data": {"contaPagarId": 999},
                                              "message": "Conta a pagar #999 criada", "warnings": []}})


async def test_confirmar_natural_um_rascunho(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "brglobal_write_api_key", "w")
    store = DraftStore(tmp_path / "n.db")
    store.create(chat_id=UID, user_id=UID, texto="x", dominio="financeiro",
                 intent="criar_conta_pagar",
                 payload={"fornecedorId": 34, "categoriaId": 15, "obraId": 4, "valor": 1,
                          "dataVencimento": "2026-06-22", "descricao": "[TESTE_AGENT_READY]"})
    m = FakeMsg("confirmar")  # sem número
    handled = await commands._maybe_pendencia_cmd(m, store, _client(_ok_post), cfgmod.settings, "confirmar")
    assert handled is True
    assert "999" in " ".join(m.replies)


async def test_confirmar_natural_varios_pede_qual(tmp_path):
    store = DraftStore(tmp_path / "n.db")
    store.create(chat_id=UID, user_id=UID, texto="a", intent="criar_conta_pagar", payload={})
    store.create(chat_id=UID, user_id=UID, texto="b", intent="criar_conta_pagar", payload={})
    m = FakeMsg("confirmar")
    handled = await commands._maybe_pendencia_cmd(m, store, None, cfgmod.settings, "confirmar")
    assert handled is True
    assert "mais de uma" in " ".join(m.replies).lower()


async def test_cancelar_natural(tmp_path):
    store = DraftStore(tmp_path / "n.db")
    d = store.create(chat_id=UID, user_id=UID, texto="x", intent="criar_conta_pagar", payload={})
    m = FakeMsg("cancela")
    handled = await commands._maybe_pendencia_cmd(m, store, None, cfgmod.settings, "cancela")
    assert handled is True
    assert store.get(d.id).status == "cancelado"


async def test_confirmar_sem_rascunho_nao_trata(tmp_path):
    store = DraftStore(tmp_path / "n.db")
    m = FakeMsg("sim")
    handled = await commands._maybe_pendencia_cmd(m, store, None, cfgmod.settings, "sim")
    assert handled is False  # cai no parser/ajuda


async def test_resolve_categoria_palavra_e_defaults(tmp_path, monkeypatch):
    f = tmp_path / "d.yaml"
    f.write_text("obraPadraoId: 4\ncontaBancariaPadraoId: 5\nformaPagamentoPadrao: pix\n"
                 "categorias:\n  areia: 15\n", encoding="utf-8")
    defaults.load_defaults(f)

    def h(req):
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": 34, "nome": "Condor"}], "ambiguo": False}}})

    d = SimpleNamespace(intent="criar_conta_pagar_paga",
                        payload_extraido={"nomeFornecedor": "Condor", "valor": 1,
                                          "categoriaPalavra": "areia", "descricao": "areia"})
    payload, faltando, pergunta = await resolve.resolver(_client(h), d)
    assert payload["fornecedorId"] == 34
    assert payload["categoriaId"] == 15           # por palavra
    assert payload["obraId"] == 4                 # default
    assert payload["contaBancariaId"] == 5        # default
    assert payload["formaPagamento"] == "pix"
    assert not faltando and pergunta is None
    assert any("categoria" in u for u in payload["_defaults_usados"])
