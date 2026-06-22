"""Roteamento de CONSULTAS FINANCEIRAS (contas a pagar reais) vs pendências locais.

Bug corrigido: "contas em aberto/vencem esta semana" caíam no fluxo de pendências
locais e respondiam "Você não tem pendências". Agora vão para a API agent-ready
(read-only) e respondem "Consultei o BRGlobal Financeiro...".
"""
from datetime import date, timedelta
from types import SimpleNamespace

import httpx

from financebot import commands, config as cfgmod
from financebot.client import FinanceClient

UID = 99


class FakeMsg:
    def __init__(self, text):
        self.text = text
        self.from_user = SimpleNamespace(id=UID)
        self.chat = SimpleNamespace(id=UID)
        self.replies = []

    async def answer(self, txt):
        self.replies.append(txt)


def _env(candidatos, total=None, hasMore=False):
    return {"data": {"ok": True, "data": {
        "candidatos": candidatos, "total": total if total is not None else len(candidatos),
        "page": 1, "limit": 200, "hasMore": hasMore}}}


def _conta(cid, forn, venc, valor=100, status="pendente", pago=None):
    return {"id": cid, "contaPagarId": cid, "fornecedor": forn, "fornecedorId": cid,
            "descricao": f"conta {cid}", "valorOriginal": valor,
            "saldoAberto": 0 if status == "pago" else valor, "status": status,
            "dataVencimento": venc, "dataPagamento": pago}


def _client(handler):
    return FinanceClient(base_url="http://t/api/agent/v1", read_key="r",
                         retries=0, transport=httpx.MockTransport(handler))


# ── Classificador (puro, determinístico) ──────────────────────────────────
def test_classifica_consultas_financeiras():
    f = commands._classificar_consulta_financeira
    assert f("Que contas tem em aberto esta semana?")["tipo"] == "semana"
    assert f("Que contas vencem esta semana?")["tipo"] == "semana"
    assert f("Tenho contas vencidas?")["tipo"] == "vencidas"
    assert f("Quais contas vencem hoje?")["tipo"] == "hoje"
    assert f("Me mostra os próximos pagamentos")["tipo"] == "proximos"
    assert f("Boletos em aberto")["tipo"] == "em_aberto"
    assert f("O que tenho para pagar?")["tipo"] == "em_aberto"
    assert f("Contas pagas")["tipo"] == "pagas"
    p = f("próximos 15 dias")
    assert p["tipo"] == "proximos" and p["dias"] == 15
    d = f("Me passa os dados para pagar a conta da Ligar")
    assert d["tipo"] == "dados_pagamento"
    assert (d["fornecedor"] or "").lower().startswith("ligar")


def test_nao_classifica_pendencias_nem_escrita():
    f = commands._classificar_consulta_financeira
    for s in ["pendências", "pendencias", "rascunhos", "meus rascunhos",
              "detalhar 3", "confirmar 3", "cancelar 3", "corrigir 3 valor 100"]:
        assert f(s) is None, s
    # frases de ESCRITA não são consulta (vão para o parser/LLM)
    for s in ["comprei um item por 1 na Ligar", "paguei 300 na carlos peças",
              "lança uma conta de 500 pra Condor amanhã",
              "comprei fio na ligar por 75,26 vence dia 25/06"]:
        assert f(s) is None, s


# ── Roteamento: consulta financeira chama a API (não pendências locais) ────
async def test_em_aberto_chama_api_e_nao_responde_pendencias():
    seen = {}
    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json=_env([_conta(1, "Ligar", "2026-06-25"),
                                              _conta(2, "Condor", "2026-06-26")], total=2))
    m = FakeMsg("Que contas tem em aberto esta semana?")
    ok = await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    assert ok is True
    joined = " ".join(m.replies)
    assert "Consultei o BRGlobal Financeiro" in joined
    assert "pendência" not in joined.lower()           # nunca fala de pendências
    assert "contas-pagar/buscar" in seen["url"] and "status=pendente" in seen["url"]


async def test_resultado_vazio_diz_consultei_e_nao_pendencias():
    def h(req):
        return httpx.Response(200, json=_env([], total=0))
    m = FakeMsg("Que contas vencem esta semana?")
    await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    joined = " ".join(m.replies)
    assert "Consultei o BRGlobal Financeiro" in joined
    assert "não encontrei contas" in joined
    assert "pendência" not in joined.lower()


async def test_vencem_hoje_usa_datavencimento(monkeypatch):
    monkeypatch.setattr(commands, "hoje_sp", lambda: date(2026, 6, 22))
    seen = {}
    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json=_env([_conta(7, "Ligar", "2026-06-22")]))
    m = FakeMsg("Quais contas vencem hoje?")
    await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    assert "dataVencimento=2026-06-22" in seen["url"] and "status=pendente" in seen["url"]
    assert "que vencem hoje" in " ".join(m.replies)


async def test_pagas_usa_status_pago_desc():
    seen = {}
    def h(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json=_env([_conta(9, "Condor", "2026-06-20",
                                                     status="pago", pago="2026-06-21")]))
    m = FakeMsg("Contas pagas")
    await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    assert "status=pago" in seen["url"] and "order=desc" in seen["url"]
    assert "pagas" in " ".join(m.replies)


async def test_semana_filtra_janela_no_cliente(monkeypatch):
    h0 = date(2026, 6, 22)
    fim = h0 + timedelta(days=(6 - h0.weekday()))
    monkeypatch.setattr(commands, "hoje_sp", lambda: h0)
    dentro1, dentro2 = h0.isoformat(), fim.isoformat()
    fora_passado = (h0 - timedelta(days=2)).isoformat()
    fora_futuro = (fim + timedelta(days=3)).isoformat()
    def h(req):
        return httpx.Response(200, json=_env([
            _conta(1, "DentroHoje", dentro1), _conta(2, "DentroFim", dentro2),
            _conta(3, "Passado", fora_passado), _conta(4, "Futuro", fora_futuro)], hasMore=False))
    m = FakeMsg("Que contas vencem esta semana?")
    await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    joined = " ".join(m.replies)
    assert "DentroHoje" in joined and "DentroFim" in joined
    assert "Passado" not in joined and "Futuro" not in joined


async def test_vencidas_so_antes_de_hoje(monkeypatch):
    h0 = date(2026, 6, 22)
    monkeypatch.setattr(commands, "hoje_sp", lambda: h0)
    def h(req):
        return httpx.Response(200, json=_env([
            _conta(1, "Vencida", (h0 - timedelta(days=5)).isoformat()),
            _conta(2, "Hoje", h0.isoformat()),
            _conta(3, "Futura", (h0 + timedelta(days=3)).isoformat())]))
    m = FakeMsg("Tenho contas vencidas?")
    await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    joined = " ".join(m.replies)
    assert "Vencida" in joined
    assert "Hoje" not in joined and "Futura" not in joined


# ── Dados de pagamento: honesto sobre Pix/código ausentes ──────────────────
async def test_dados_pagamento_uma_conta_sem_pix():
    def h(req):
        return httpx.Response(200, json=_env([_conta(123, "Ligar", "2026-06-25")]))
    m = FakeMsg("me passa os dados para pagar a conta da Ligar")
    await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    joined = " ".join(m.replies)
    assert "Conta ID: 123" in joined
    assert "não retornou Pix" in joined            # honesto, sem inventar


async def test_dados_pagamento_varias_pede_escolha():
    def h(req):
        return httpx.Response(200, json=_env([_conta(1, "Ligar", "2026-06-25"),
                                              _conta(2, "Ligar", "2026-06-28")]))
    m = FakeMsg("me passa os dados para pagar a conta da Ligar")
    await commands._maybe_consulta_financeira(m, _client(h), m.text.lower())
    assert "mais de uma conta da" in " ".join(m.replies).lower()


# ── Pendências locais continuam locais (regressão) ─────────────────────────
async def test_pendencias_nao_vira_consulta_financeira():
    def h(req):
        raise AssertionError("não deveria chamar a API para 'pendências'")
    for s in ["pendências", "detalhar 3", "confirmar 3"]:
        m = FakeMsg(s)
        ok = await commands._maybe_consulta_financeira(m, _client(h), s.lower())
        assert ok is False and m.replies == []


# ── Caminho via LLM (intent=consulta + consultaTipo) ───────────────────────
async def test_ordem_freeform_pendencia_nao_captura_financeira(tmp_path):
    """Cenário do bug: a frase financeira passa pelo roteamento de pendências (False)
    e é capturada pela consulta financeira (True)."""
    from financebot.drafts import DraftStore
    store = DraftStore(tmp_path / "p.db")
    def h(req):
        return httpx.Response(200, json=_env([_conta(1, "Ligar", "2026-06-25")]))
    cli = _client(h)
    m = FakeMsg("Que contas tem em aberto esta semana?")
    handled = await commands._maybe_pendencia_cmd(m, store, cli, cfgmod.settings, m.text.lower())
    assert handled is False                      # pendência local NÃO captura
    ok = await commands._maybe_consulta_financeira(m, cli, m.text.lower())
    assert ok is True                            # consulta financeira captura
    assert "Consultei o BRGlobal Financeiro" in " ".join(m.replies)


async def test_tratar_parse_consulta_via_llm(monkeypatch):
    monkeypatch.setattr(commands, "hoje_sp", lambda: date(2026, 6, 22))
    def h(req):
        return httpx.Response(200, json=_env([_conta(1, "Ligar",
                                                     (date(2026, 6, 22) - timedelta(days=1)).isoformat())]))
    m = FakeMsg("tem conta atrasada?")
    parsed = {"intent": "consulta", "reply": "Deixa eu ver.",
              "fields": {"consultaTipo": "vencidas"}}
    await commands._tratar_parse(m, None, _client(h), parsed)
    joined = " ".join(m.replies)
    assert "Consultei o BRGlobal Financeiro" in joined and "vencidas" in joined
