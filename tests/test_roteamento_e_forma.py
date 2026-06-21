"""Roteamento de pendências (detalhar/confirmar/cancelar sem número) + forma de pagamento padrão
+ fornecedor 'Outros'. Garante que palavras de controle NUNCA caem na LLM."""
import httpx
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


def _client():
    def h(req):
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": 33, "nome": "Ligar"}], "ambiguo": False}}})
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(h))


def _store_varias(tmp_path, n=3):
    s = DraftStore(tmp_path / "r.db")
    for i in range(n):
        s.create(chat_id=UID, user_id=UID, texto=f"x{i}", intent="criar_conta_pagar", payload={})
    return s


# ── A/B/C: palavras de controle não vão p/ LLM; com várias pendências pedem número ──
async def test_detalhar_varias_pede_numero(tmp_path):
    s = _store_varias(tmp_path)
    m = FakeMsg("detalhar")
    handled = await commands._maybe_pendencia_cmd(m, s, _client(), cfgmod.settings, "detalhar")
    assert handled is True
    assert "detalhar" in " ".join(m.replies).lower() and "3" in " ".join(m.replies)


async def test_confirmar_varias_pede_numero(tmp_path):
    s = _store_varias(tmp_path)
    m = FakeMsg("confirmar")
    handled = await commands._maybe_pendencia_cmd(m, s, _client(), cfgmod.settings, "confirmar")
    assert handled is True
    assert "mais de uma" in " ".join(m.replies).lower()


async def test_cancelar_varias_pede_numero(tmp_path):
    s = _store_varias(tmp_path)
    m = FakeMsg("cancelar")
    handled = await commands._maybe_pendencia_cmd(m, s, _client(), cfgmod.settings, "cancelar")
    assert handled is True
    assert "mais de uma" in " ".join(m.replies).lower()


async def test_detalhar_sozinho_sem_pendencia_nao_vai_llm(tmp_path):
    s = DraftStore(tmp_path / "r.db")
    m = FakeMsg("detalhar")
    handled = await commands._maybe_pendencia_cmd(m, s, _client(), cfgmod.settings, "detalhar")
    assert handled is True  # tratado (não cai no parser)


# ── D/E: forma de pagamento padrão pix; "de outro jeito" → outro ──
def _setup_defaults(tmp_path):
    f = tmp_path / "d.yaml"
    f.write_text(
        "obraPadraoId: 4\ncategoriaPadraoId: 15\nformaPagamentoPadrao: pix\n"
        "contaBancariaPadraoId: 5\nfornecedorOutrosId: 6\n"
        "contasBancarias:\n  conta1: 5\n  conta2: 6\n"
        "categorias:\n  cabo: 15\n", encoding="utf-8")
    defaults.load_defaults(f)


async def test_forma_padrao_pix(tmp_path):
    _setup_defaults(tmp_path)
    d = SimpleNamespace(intent="criar_conta_pagar_paga", texto_original="comprei 11 cabos de vassoura por 35 na Ligar",
                        payload_extraido={"nomeFornecedor": "Ligar", "descricao": "11 cabos de vassoura",
                                          "valor": 35})
    p, falt, perg = await resolve.resolver(_client(), d)
    assert p["formaPagamento"] == "pix"
    assert p["contaBancariaId"] == 5 and p["categoriaId"] == 15 and p["obraId"] == 4
    assert not falt and perg is None


async def test_forma_outro_so_se_disser(tmp_path):
    _setup_defaults(tmp_path)
    # LLM devolveu "outro" mas o texto diz "de outro jeito" → mantém outro
    d = SimpleNamespace(intent="criar_conta_pagar_paga",
                        texto_original="comprei 11 cabos por 35 na Ligar de outro jeito",
                        payload_extraido={"nomeFornecedor": "Ligar", "valor": 35, "formaPagamento": "outro"})
    p, _, _ = await resolve.resolver(_client(), d)
    assert p["formaPagamento"] == "outro"


async def test_forma_outro_sem_texto_vira_pix(tmp_path):
    _setup_defaults(tmp_path)
    # LLM devolveu "outro" mas o texto NÃO menciona → sobrescreve para pix
    d = SimpleNamespace(intent="criar_conta_pagar_paga",
                        texto_original="comprei 11 cabos por 35 na Ligar",
                        payload_extraido={"nomeFornecedor": "Ligar", "valor": 35, "formaPagamento": "outro"})
    p, _, _ = await resolve.resolver(_client(), d)
    assert p["formaPagamento"] == "pix"


# ── F: fornecedor não encontrado → Outros (6) + marcador ──
async def test_fornecedor_nao_encontrado_outros(tmp_path):
    _setup_defaults(tmp_path)

    def h(req):  # zero candidatos
        return httpx.Response(200, json={"data": {"ok": True, "data": {"candidatos": [], "ambiguo": False}}})
    cli = FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                        retries=0, transport=httpx.MockTransport(h))
    d = SimpleNamespace(intent="criar_conta_pagar_paga",
                        texto_original="comprei um rolo de fio 2,5 mm no Wallace por 298 reais",
                        payload_extraido={"nomeFornecedor": "Wallace", "valor": 298, "descricao": "rolo de fio"})
    p, falt, perg = await resolve.resolver(cli, d)
    assert p["fornecedorId"] == 6
    assert "AJUSTAR FORNECEDOR" in p["observacoes"] and "Wallace" in p["observacoes"]
    assert not falt and perg is None
