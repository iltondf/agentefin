"""Slot-filling: quando o bot pergunta um campo, a próxima mensagem preenche o rascunho
(em vez de virar nova conversa). Reproduz o bug 'descrição? → alicate'."""
import httpx
from types import SimpleNamespace

from financebot import commands, config as cfgmod
from financebot.client import FinanceClient
from financebot.drafts import DraftStore

UID = 8646895490


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
        # fornecedor resolve único
        return httpx.Response(200, json={"data": {"ok": True, "data": {
            "candidatos": [{"id": 34, "nome": "Condor"}], "ambiguo": False}}})
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r", write_key="w",
                         retries=0, transport=httpx.MockTransport(h))


async def test_slot_filling_descricao(tmp_path, monkeypatch):
    # defaults com categoria/obra/conta para não faltar mais nada além da descrição
    from financebot import defaults
    f = tmp_path / "d.yaml"
    f.write_text("obraPadraoId: 4\ncontaBancariaPadraoId: 5\nformaPagamentoPadrao: pix\n"
                 "categorias:\n  alicate: 15\n  ferramenta: 15\n", encoding="utf-8")
    defaults.load_defaults(f)

    store = DraftStore(tmp_path / "s.db")
    # rascunho criado pela LLM, aguardando a descrição
    d = store.create(chat_id=UID, user_id=UID, texto="lança conta de R$1 pra Condor amanhã",
                     dominio="financeiro", intent="criar_conta_pagar",
                     payload={"nomeFornecedor": "Condor", "valor": 1, "dataVencimento": "amanha"})
    commands._set_aguardando(store, d, "descricao")
    assert store.get(d.id).payload_extraido["_aguardando_campo"] == "descricao"

    # usuário responde "alicate" — deve PREENCHER, não virar conversa
    m = FakeMsg("alicate")
    handled = await commands._maybe_pendencia_cmd(m, store, _client(), cfgmod.settings, "alicate")
    assert handled is True
    got = store.get(d.id)
    assert got.payload_extraido["descricao"] == "alicate"
    assert "_aguardando_campo" not in got.payload_extraido
    # resolveu tudo (defaults) → foi para aguardando_confirmacao com resumo
    assert got.status == "aguardando_confirmacao"
    assert "CONFIRMAR" in " ".join(m.replies)


async def test_nova_compra_nao_e_capturada_como_resposta(tmp_path):
    """Bug real: havia rascunho aguardando 'descricao'; usuário manda nova compra completa.
    A frase NÃO pode preencher a descrição do rascunho antigo (deve cair no parser → novo rascunho)."""
    store = DraftStore(tmp_path / "s.db")
    d = store.create(chat_id=UID, user_id=UID, texto="conta antiga", dominio="financeiro",
                     intent="criar_conta_pagar", payload={"nomeFornecedor": "X", "valor": 1})
    commands._set_aguardando(store, d, "descricao")
    m = FakeMsg("comprei 11 cabos de vassoura por 35 na Ligar")
    handled = await commands._maybe_pendencia_cmd(
        m, store, _client(), cfgmod.settings, m.text.lower())
    assert handled is False  # NÃO capturou → vai para o parser (novo rascunho)
    # rascunho antigo permanece intacto (descrição não virou a frase nova)
    assert store.get(d.id).payload_extraido.get("descricao") in (None, "")


async def test_resposta_curta_ainda_preenche(tmp_path):
    """Resposta curta (sem verbo) continua preenchendo o campo aguardado."""
    from financebot import defaults
    f = tmp_path / "d.yaml"
    f.write_text("obraPadraoId: 4\ncontaBancariaPadraoId: 5\ncategoriaPadraoId: 15\n"
                 "formaPagamentoPadrao: pix\n", encoding="utf-8")
    defaults.load_defaults(f)
    store = DraftStore(tmp_path / "s.db")
    d = store.create(chat_id=UID, user_id=UID, texto="conta", dominio="financeiro",
                     intent="criar_conta_pagar",
                     payload={"nomeFornecedor": "Condor", "valor": 1, "dataVencimento": "amanha"})
    commands._set_aguardando(store, d, "descricao")
    m = FakeMsg("cabos de vassoura")
    handled = await commands._maybe_pendencia_cmd(m, store, _client(), cfgmod.settings,
                                                  "cabos de vassoura")
    assert handled is True
    assert store.get(d.id).payload_extraido["descricao"] == "cabos de vassoura"


async def test_confirmar_ainda_funciona_com_aguardando(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "write_enabled", False)
    store = DraftStore(tmp_path / "s.db")
    d = store.create(chat_id=UID, user_id=UID, texto="x", dominio="financeiro",
                     intent="criar_conta_pagar", payload={"_aguardando_campo": "descricao"})
    # 'confirmar' NÃO deve ser capturado como preenchimento de campo
    m = FakeMsg("confirmar")
    await commands._maybe_pendencia_cmd(m, store, _client(), cfgmod.settings, "confirmar")
    # como write off, confirma mas não grava; o importante: não virou descrição="confirmar"
    assert store.get(d.id).payload_extraido.get("descricao") != "confirmar"
