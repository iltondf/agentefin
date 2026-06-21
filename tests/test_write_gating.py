"""Garantias de segurança da escrita: gating, idempotência, validação. SEM POST real."""
import httpx
import pytest

from financebot import config as cfgmod
from financebot.client import FinanceClient
from financebot.tools_write import (
    WRITE_TOOLS, executar_write, gerar_idempotency_key, validar_payload,
)


class _Draft:
    def __init__(self, status="confirmado", payload=None):
        self.id = 1
        self.status = status
        self.payload_extraido = payload or {}


def _client(handler=None):
    h = handler or (lambda r: httpx.Response(200, json={"data": {"ok": True, "data": {"contaPagarId": 1}}}))
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(h))


def test_idempotency_key_formato_estavel():
    k1 = gerar_idempotency_key(chat_id=10, draft_id=5, intent="criar_conta_pagar", ts_min="202606211200")
    k2 = gerar_idempotency_key(chat_id=10, draft_id=5, intent="criar_conta_pagar", ts_min="202606211200")
    assert k1 == k2 == "tg:10:5:criar_conta_pagar:202606211200"
    assert "Bearer" not in k1 and "key" not in k1.lower()  # sem segredo


def test_validar_payload_detecta_faltando():
    tool = WRITE_TOOLS["criar_conta_pagar"]
    faltando = validar_payload(tool, {"fornecedorId": 1})
    assert "categoriaId" in faltando and "valor" in faltando


def test_validar_payload_valor_negativo():
    tool = WRITE_TOOLS["criar_lancamento_rh"]
    faltando = validar_payload(tool, {"funcionarioId": 1, "tipo": "diaria_extra",
                                      "data": "2026-06-21", "qtd": 1, "valorUnit": -5})
    assert "valorUnit>0" in faltando


async def test_nao_posta_sem_write_enabled(monkeypatch):
    # WRITE_ENABLED desligado → nunca chama POST
    monkeypatch.setattr(cfgmod.settings, "write_enabled", False)
    monkeypatch.setattr(cfgmod.settings, "brglobal_write_api_key", "w")
    called = {"post": False}
    def h(r):
        called["post"] = True
        return httpx.Response(200, json={"data": {"ok": True, "data": {}}})
    res = await executar_write(_client(h), intent="criar_conta_pagar",
                               draft=_Draft(payload={"fornecedorId": 1, "categoriaId": 2,
                                            "descricao": "[TESTE]", "valor": 1, "dataVencimento": "2026-06-22"}),
                               idempotency_key="tg:1:1:x:202606")
    assert res.ok is False
    assert called["post"] is False
    assert res.error_kind == "disabled"


async def test_nao_posta_sem_confirmacao(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "brglobal_write_api_key", "w")
    called = {"post": False}
    def h(r):
        called["post"] = True
        return httpx.Response(200, json={"data": {"ok": True, "data": {}}})
    res = await executar_write(_client(h), intent="criar_conta_pagar",
                               draft=_Draft(status="pendente", payload={"fornecedorId": 1}),
                               idempotency_key="k")
    assert res.ok is False and called["post"] is False
    assert res.error_kind == "confirm"


async def test_posta_quando_tudo_ok(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "brglobal_write_api_key", "w")
    seen = {}
    def h(req):
        seen["idem"] = req.headers.get("idempotency-key")
        return httpx.Response(201, json={"data": {"ok": True, "data": {"contaPagarId": 77}}})
    res = await executar_write(_client(h), intent="criar_conta_pagar",
                               draft=_Draft(payload={"fornecedorId": 1, "categoriaId": 2,
                                            "descricao": "[TESTE_AGENT_READY] x", "valor": 1,
                                            "dataVencimento": "2026-06-22"}),
                               idempotency_key="tg:1:1:cp:202606")
    assert res.ok is True
    assert res.data["data"]["contaPagarId"] == 77
    assert seen["idem"] == "tg:1:1:cp:202606"
