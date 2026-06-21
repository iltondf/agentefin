import httpx

from financebot.client import FinanceClient
from financebot.tools import build_read_registry, read_tool_names


def _client(handler):
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r",
                         retries=0, transport=httpx.MockTransport(handler))


def test_registry_tem_tools_antigas_e_novas():
    reg = build_read_registry(_client(lambda r: httpx.Response(200, json={"data": {}})))
    nomes = read_tool_names(reg)
    # antigas (legacy)
    for n in ["consultar_whoami", "consultar_contas_hoje", "consultar_resumo_diario",
              "consultar_painel_operacional"]:
        assert n in nomes
    # novas (v2)
    for n in ["buscar_funcionarios", "buscar_fornecedores", "buscar_obras",
              "buscar_terceirizados", "buscar_contas_pagar", "consultar_fechamento_rh"]:
        assert n in nomes
    assert all(reg[n].kind == "read" for n in nomes)


async def test_tool_legacy_chama_endpoint_certo():
    seen = {}
    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": {"data": [], "total": 0}})
    reg = build_read_registry(_client(h))
    res = await reg["consultar_contas_hoje"].run({})
    assert res.ok
    assert "contas-pagar/hoje" in seen["url"]


async def test_tool_v2_busca_envia_nome():
    seen = {}
    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": {"ok": True, "data": {"candidatos": []}}})
    reg = build_read_registry(_client(h))
    await reg["buscar_fornecedores"].run({"nome": "Areião"})
    assert "financeiro/fornecedores/buscar" in seen["url"]
    assert "nome=" in seen["url"]


async def test_buscar_contas_pagar_repassa_filtros_e_ordena_por_padrao():
    """contas-pagar/buscar reescrito: repassa filtros novos e usa createdAt desc por padrão."""
    seen = {}
    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": 932, "contaPagarId": 932}], "total": 1,
            "page": 1, "limit": 10, "hasMore": False}}})
    reg = build_read_registry(_client(h))
    res = await reg["buscar_contas_pagar"].run(
        {"status": "pago", "fornecedorId": 33, "valor": 1, "dataPagamento": "2026-06-21", "limit": 10})
    assert res.ok
    url = seen["url"]
    assert "financeiro/contas-pagar/buscar" in url
    for frag in ("status=pago", "fornecedorId=33", "valor=1", "dataPagamento=2026-06-21",
                 "limit=10", "orderBy=createdAt", "order=desc"):
        assert frag in url, frag
    # leitura no aninhamento data.data
    assert res.data["data"]["candidatos"][0]["contaPagarId"] == 932


async def test_buscar_contas_pagar_ignora_param_desconhecido():
    """Param fora do whitelist não é repassado (servidor é STRICT → evitaria 422)."""
    seen = {}
    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": {"ok": True, "data": {"candidatos": []}}})
    reg = build_read_registry(_client(h))
    await reg["buscar_contas_pagar"].run({"fornecedor": "Ligar", "xpto": "1", "obraId": 4})
    url = seen["url"]
    assert "fornecedor=Ligar" in url and "obraId=4" in url
    assert "xpto" not in url
