import httpx
import pytest

from financebot.client import FinanceAPIError, FinanceClient


def _client(handler, retries=2):
    return FinanceClient(
        base_url="http://test/api/agent/v1",
        read_key="k",
        write_key="w",
        retries=retries,
        transport=httpx.MockTransport(handler),
    )


async def test_unwrap_envelope():
    def h(_req):
        return httpx.Response(200, json={"apiVersion": "v1", "data": {"data": [{"id": 1}], "total": 1}})

    data = await _client(h).contas_pagar_hoje()
    assert data["total"] == 1
    assert data["data"][0]["id"] == 1


async def test_sends_bearer_header():
    seen = {}

    def h(req):
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"data": {}})

    await _client(h).whoami()
    assert seen["auth"] == "Bearer k"


async def test_401_auth():
    def h(_req):
        return httpx.Response(401, json={"error": "AGENT_AUTH_REQUIRED"})

    with pytest.raises(FinanceAPIError) as ei:
        await _client(h).contas_pagar_hoje()
    assert ei.value.kind == "auth"
    assert ei.value.status == 401


async def test_403_scope():
    def h(_req):
        return httpx.Response(403, json={})

    with pytest.raises(FinanceAPIError) as ei:
        await _client(h).contas_pagar_hoje()
    assert ei.value.kind == "scope"


async def test_503_disabled():
    def h(_req):
        return httpx.Response(503, json={})

    with pytest.raises(FinanceAPIError) as ei:
        await _client(h).whoami()
    assert ei.value.kind == "disabled"


async def test_retry_429_then_200():
    state = {"n": 0}

    def h(_req):
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"data": {"data": [], "total": 0}})

    data = await _client(h, retries=2).contas_pagar_hoje()
    assert state["n"] == 2
    assert data["total"] == 0


async def test_500_exhausts_retries():
    state = {"n": 0}

    def h(_req):
        state["n"] += 1
        return httpx.Response(500, json={})

    with pytest.raises(FinanceAPIError) as ei:
        await _client(h, retries=1).contas_pagar_hoje()
    assert ei.value.kind == "http"
    assert state["n"] == 2  # 1 tentativa + 1 retry


async def test_parse_error():
    def h(_req):
        return httpx.Response(200, text="isto não é json")

    with pytest.raises(FinanceAPIError) as ei:
        await _client(h).whoami()
    assert ei.value.kind == "parse"


async def test_proximos_passes_dias_param():
    seen = {}

    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": {"data": [], "total": 0}})

    await _client(h).contas_pagar_proximos(7)
    assert "dias=7" in seen["url"]
    assert "proximos-dias" in seen["url"]


async def test_404_not_retried():
    state = {"n": 0}

    def h(_req):
        state["n"] += 1
        return httpx.Response(404, json={})

    with pytest.raises(FinanceAPIError) as ei:
        await _client(h, retries=2).contas_pagar_hoje()
    assert ei.value.kind == "http"
    assert ei.value.status == 404
    assert state["n"] == 1  # 404 não deve ser retentado
