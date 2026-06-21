"""Modo conversacional: intent=conversa não cria rascunho; cálculo+lançamento cria."""
import httpx
from types import SimpleNamespace

from financebot import commands, config as cfgmod
from financebot.client import FinanceClient
from financebot.drafts import DraftStore

UID = 5


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
        if req.method == "GET":
            return httpx.Response(200, json={"data": {"ok": True, "data": {
                "candidatos": [{"id": 10, "nome": "Vanderli"}], "ambiguo": False}}})
        return httpx.Response(200, json={"data": {"ok": True, "data": {"lancamentoId": 1}}})
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(h))


async def test_conversa_nao_cria_rascunho(tmp_path):
    store = DraftStore(tmp_path / "c.db")
    m = FakeMsg("quanto é 325 + 325?")
    parsed = {"reply": "325 + 325 = 650.", "intent": "conversa",
              "calculos": [{"expressao": "325 + 325", "resultado": 650}],
              "fields": {}, "missing": [], "shouldAsk": False}
    await commands._tratar_parse(m, store, _client(), parsed)
    assert "650" in " ".join(m.replies)
    assert store.list_active(UID) == []   # nenhum rascunho


async def test_calculo_vira_lancamento_pergunta_destino(tmp_path):
    store = DraftStore(tmp_path / "c.db")
    m = FakeMsg("soma 325 + 325 e adiciona no Vanderli")
    parsed = {"reply": "Calculei 325+325=650 para Vanderli.",
              "intent": "criar_lancamento_rh", "confidence": 0.86,
              "fields": {"nomeFuncionario": "Vanderli", "tipo": "ajuste_positivo",
                         "destino": None, "qtd": 1, "valorUnit": 650, "data": "hoje"},
              "calculos": [{"expressao": "325 + 325", "resultado": 650}],
              "missing": ["destino"], "shouldAsk": True, "question": "Vale ou pagamento?"}
    await commands._tratar_parse(m, store, _client(), parsed)
    joined = " ".join(m.replies)
    assert "650" in joined and "agamento" in joined.lower()  # reply + pergunta
    drafts = store.list_active(UID)
    assert len(drafts) == 1
    assert drafts[0].payload_extraido["valorUnit"] == 650


async def test_indefinido_usa_reply(tmp_path):
    store = DraftStore(tmp_path / "c.db")
    m = FakeMsg("bom dia")
    parsed = {"reply": "Bom dia! Como posso ajudar?", "intent": "conversa",
              "fields": {}, "missing": [], "shouldAsk": False}
    await commands._tratar_parse(m, store, _client(), parsed)
    assert "Bom dia" in " ".join(m.replies)
