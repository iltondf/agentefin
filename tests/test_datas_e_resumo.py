"""Datas determinísticas (texto cru > LLM, que alucina o ano) + resumo sem
'Falta: formaPagamento' fantasma depois que o Pix padrão já preencheu."""
from datetime import date, timedelta
from types import SimpleNamespace

import httpx

from financebot import commands, defaults, resolve
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


def _client(nome="Ligar", fid=33):
    def h(req):
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": fid, "nome": nome}], "ambiguo": False}}})
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(h))


def _yaml(tmp_path):
    f = tmp_path / "d.yaml"
    f.write_text("obraPadraoId: 4\ncategoriaPadraoId: 15\nformaPagamentoPadrao: pix\n"
                 "contaBancariaPadraoId: 5\n", encoding="utf-8")
    defaults.load_defaults(f)


# ── _data_do_texto (unitário) ──────────────────────────────────────────────
def test_data_dia_mes_sem_ano_usa_ano_atual():
    ano = date.today().year
    assert resolve._data_do_texto("vence dia 25/06") == f"{ano}-06-25"
    assert resolve._data_do_texto("comprei fio, vence 25/06") == f"{ano}-06-25"


def test_data_com_ano_explicito_respeitado():
    assert resolve._data_do_texto("vence 25/06/2027") == "2027-06-25"
    assert resolve._data_do_texto("vence 25/06/27") == "2027-06-25"


def test_data_relativos_e_por_extenso():
    hoje = date.today()
    assert resolve._data_do_texto("paguei hoje") == hoje.isoformat()
    assert resolve._data_do_texto("vence amanhã") == (hoje + timedelta(days=1)).isoformat()
    assert resolve._data_do_texto("vence dia 25 de junho") == f"{hoje.year}-06-25"


def test_sem_data_no_texto_retorna_none():
    assert resolve._data_do_texto("comprei 11 cabos por 35 na Ligar") is None
    assert resolve._data_do_texto("comprei cimento por 60 na Condor") is None


# ── resolver: texto manda; ano/data alucinada pela LLM é ignorada ──────────
async def test_resolve_usa_texto_e_ignora_ano_alucinado(tmp_path):
    _yaml(tmp_path)
    ano = date.today().year
    d = SimpleNamespace(intent="criar_conta_pagar",
                        texto_original="comprei fio na ligar por 75,26 vence dia 25/06",
                        payload_extraido={"nomeFornecedor": "Ligar", "valor": 75.26,
                                          "descricao": "fio", "dataVencimento": "2023-06-25"})
    payload, faltando, pergunta = await resolve.resolver(_client(), d)
    assert payload["dataVencimento"] == f"{ano}-06-25"   # NÃO 2023


async def test_resolve_sem_data_no_texto_vira_hoje(tmp_path):
    _yaml(tmp_path)
    hoje = date.today().isoformat()
    # paga, sem data no texto; LLM alucinou dataPagamento 2025-03-29 → deve virar hoje
    d = SimpleNamespace(intent="criar_conta_pagar_paga",
                        texto_original="comprei cimento por 60 na Condor",
                        payload_extraido={"nomeFornecedor": "Condor", "valor": 60,
                                          "descricao": "cimento", "dataPagamento": "2025-03-29"})
    payload, faltando, pergunta = await resolve.resolver(_client("Condor", 34), d)
    assert payload["dataPagamento"] == hoje
    assert payload["dataVencimento"] == hoje


# ── resumo não mostra "Falta: formaPagamento" após Pix padrão ──────────────
async def test_resumo_sem_falta_fantasma_apos_defaults(tmp_path):
    _yaml(tmp_path)
    store = DraftStore(tmp_path / "r.db")
    m = FakeMsg("comprei 11 cabos de vassoura por 35 na Ligar")
    parsed = {"reply": "Anotando.", "intent": "criar_conta_pagar_paga",
              "fields": {"nomeFornecedor": "Ligar", "descricao": "11 cabos de vassoura",
                         "valor": 35},
              # a LLM marcou esses como faltantes, mas têm default → não pode sobrar "Falta"
              "missing": ["formaPagamento", "contaBancariaId"], "shouldAsk": False}
    await commands._tratar_parse(m, store, _client(), parsed)
    joined = " ".join(m.replies)
    assert "CONFIRMAR" in joined
    assert "Falta" not in joined            # sem "⚠️ Falta: ..."
    assert "formaPagamento" not in joined   # campo cru não aparece (só o label "Forma")
    assert "pix" in joined.lower()
    d = store.list_active(UID)[0]
    assert "formaPagamento" not in (d.campos_faltando or [])
