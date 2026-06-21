import httpx
import pytest

from financebot.client import FinanceAPIError, FinanceClient


def _client(handler):
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(handler))


async def test_unwrap_v2_success():
    # envelope.data.data (recurso real aninhado)
    def h(_r):
        return httpx.Response(200, json={"apiVersion": "v1", "data": {
            "ok": True, "data": {"candidatos": [{"id": 5, "nome": "Vanderli"}], "ambiguo": False},
            "message": "ok", "warnings": [], "nextAction": None}})
    out = await _client(h).get_v2("rh/funcionarios/buscar", {"nome": "Vanderli"})
    assert out["data"]["candidatos"][0]["id"] == 5
    assert out["warnings"] == []


async def test_unwrap_v2_error_ambiguo():
    def h(_r):
        return httpx.Response(422, json={"apiVersion": "v1", "data": None, "error": {
            "ok": False, "errorCode": "AMBIGUO", "precisaConfirmar": False,
            "message": "mais de um", "candidatos": [{"id": 1}, {"id": 2}], "camposFaltando": []}})
    with pytest.raises(FinanceAPIError) as ei:
        await _client(h).get_v2("financeiro/fornecedores/buscar", {"nome": "Areia"})
    e = ei.value
    assert e.error_code == "AMBIGUO"
    assert len(e.candidatos) == 2


async def test_post_requires_write_key():
    def h(_r):
        return httpx.Response(200, json={"data": {"ok": True, "data": {"contaPagarId": 1}}})
    c = FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="",
                      retries=0, transport=httpx.MockTransport(h))
    with pytest.raises(FinanceAPIError) as ei:
        await c.post_v2("financeiro/contas-pagar", {"x": 1}, idempotency_key="k")
    assert ei.value.error_code == "SEM_PERMISSAO"


async def test_post_sends_idempotency_and_write_bearer():
    seen = {}
    def h(req):
        seen["auth"] = req.headers.get("authorization")
        seen["idem"] = req.headers.get("idempotency-key")
        return httpx.Response(201, json={"data": {"ok": True, "data": {"contaPagarId": 9}}})
    out = await _client(h).post_v2("financeiro/contas-pagar", {"v": 1}, idempotency_key="tg:1:2:x:202606")
    assert seen["auth"] == "Bearer w"          # usa a chave de ESCRITA
    assert seen["idem"] == "tg:1:2:x:202606"
    assert out["data"]["contaPagarId"] == 9


async def test_post_replay_idempotente_warning():
    def h(_r):
        return httpx.Response(200, json={"data": {"ok": True, "data": {"contaPagarId": 9},
            "warnings": ["Resposta idempotente (replay) — nada foi duplicado."]}})
    out = await _client(h).post_v2("financeiro/contas-pagar", {"v": 1}, idempotency_key="same")
    assert "idempotente" in out["warnings"][0]


async def test_legacy_unwrap_still_works():
    def h(_r):
        return httpx.Response(200, json={"apiVersion": "v1", "data": {"data": [], "total": 0}})
    out = await _client(h).contas_pagar_hoje()
    assert out["total"] == 0
