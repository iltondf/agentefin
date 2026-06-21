"""Resolução de conta bancária de saída: alias/final/padrão, conforme regras do operador."""
import httpx
from types import SimpleNamespace

from financebot import defaults, resolve
from financebot.client import FinanceClient


def _client():
    def h(req):  # fornecedor Ligar resolve único
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": 33, "nome": "Ligar"}], "ambiguo": False}}})
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(h))


def _setup_defaults(tmp_path):
    f = tmp_path / "d.yaml"
    f.write_text(
        "obraPadraoId: 4\ncategoriaPadraoId: 15\nformaPagamentoPadrao: pix\n"
        "contaBancariaPadraoId: 5\n"
        "contasBancarias:\n  conta1: 5\n  contaUm: 5\n  final85: 5\n  \"85\": 5\n"
        "  conta2: 6\n  contaDois: 6\n  final97: 6\n  \"97\": 6\n",
        encoding="utf-8")
    defaults.load_defaults(f)


def _draft(fields):
    return SimpleNamespace(intent="criar_conta_pagar_paga", payload_extraido=fields)


async def test_ex1_sem_forma_sem_conta(tmp_path):
    _setup_defaults(tmp_path)
    p, falt, perg = await resolve.resolver(_client(), _draft(
        {"nomeFornecedor": "Ligar", "descricao": "11 cabos de vassoura", "valor": 35}))
    assert p["formaPagamento"] == "pix"
    assert p["contaBancariaId"] == 5      # padrão final 85
    assert p["categoriaId"] == 15 and p["obraId"] == 4
    assert not falt and perg is None


async def test_ex2_dinheiro_conta2(tmp_path):
    _setup_defaults(tmp_path)
    p, falt, perg = await resolve.resolver(_client(), _draft(
        {"nomeFornecedor": "Ligar", "valor": 85, "formaPagamento": "dinheiro",
         "contaBancariaAlias": "conta2"}))
    assert p["formaPagamento"] == "dinheiro"
    assert p["contaBancariaId"] == 6      # final 97
    assert not falt and perg is None


async def test_ex3_pix_conta1(tmp_path):
    _setup_defaults(tmp_path)
    p, falt, perg = await resolve.resolver(_client(), _draft(
        {"nomeFornecedor": "Ligar", "valor": 120, "formaPagamento": "pix",
         "contaBancariaAlias": "conta1"}))
    assert p["contaBancariaId"] == 5      # final 85


async def test_ex4_pix_final97(tmp_path):
    _setup_defaults(tmp_path)
    p, falt, perg = await resolve.resolver(_client(), _draft(
        {"nomeFornecedor": "Ligar", "valor": 120, "formaPagamento": "pix",
         "contaBancariaFinal": "97"}))
    assert p["contaBancariaId"] == 6      # final 97


async def test_conta_desconhecida_pergunta(tmp_path):
    _setup_defaults(tmp_path)
    p, falt, perg = await resolve.resolver(_client(), _draft(
        {"nomeFornecedor": "Ligar", "valor": 10, "contaBancariaAlias": "conta9"}))
    assert "contaBancariaId" in falt
    assert "conta" in perg.lower()
