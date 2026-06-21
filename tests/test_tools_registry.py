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
