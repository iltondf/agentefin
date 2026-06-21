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


# ── "comprei ... vence dia X" = conta a pagar PENDENTE (não paga) ──────────
def test_reclassifica_vence_sem_pagamento_vira_pendente():
    assert commands._reclassificar_conta(
        "criar_conta_pagar_paga", "comprei fio na ligar por 75,26 vence dia 25/06"
    ) == "criar_conta_pagar"


def test_reclassifica_nao_mexe_sem_sinal_de_vencimento():
    # "pela conta 2" = pagou de uma conta → continua paga
    assert commands._reclassificar_conta(
        "criar_conta_pagar_paga", "comprei cimento por 60 na Condor pela conta 2"
    ) == "criar_conta_pagar_paga"


def test_reclassifica_respeita_pagamento_explicito():
    # tem 'vence' mas disse que já pagou → continua paga
    assert commands._reclassificar_conta(
        "criar_conta_pagar_paga", "comprei X vence dia 25/06 mas ja paguei"
    ) == "criar_conta_pagar_paga"


def test_reclassifica_nao_toca_outros_intents():
    assert commands._reclassificar_conta("criar_lancamento_rh", "vence amanhã") == "criar_lancamento_rh"
    assert commands._reclassificar_conta("criar_conta_pagar", "vence dia 25/06") == "criar_conta_pagar"


def test_sanitizar_fields_remove_pagamento_em_pendente():
    f = {"nomeFornecedor": "Ligar", "valor": 1, "dataPagamento": "2025-06-25",
         "formaPagamento": "pix", "contaBancariaId": 5}
    out = commands._sanitizar_fields("criar_conta_pagar", f)
    assert "dataPagamento" not in out and "formaPagamento" not in out
    assert "contaBancariaId" not in out
    assert out["nomeFornecedor"] == "Ligar"  # preserva o resto


def test_sanitizar_fields_preserva_em_conta_paga():
    f = {"valor": 1, "dataPagamento": "2026-06-21", "formaPagamento": "pix"}
    out = commands._sanitizar_fields("criar_conta_pagar_paga", f)
    assert out["dataPagamento"] == "2026-06-21" and out["formaPagamento"] == "pix"


async def test_fluxo_comprei_vence_vira_pendente_sem_pago_em(tmp_path):
    _yaml(tmp_path)
    store = DraftStore(tmp_path / "r.db")
    ano = date.today().year
    m = FakeMsg("comprei fio na ligar por 75,26 vence dia 25/06")
    parsed = {"reply": "Anotado, paga no dia 25/06. Qual a forma?",
              "intent": "criar_conta_pagar_paga",   # LLM classificou errado (paga)
              # a LLM vazou dataPagamento/forma alucinados nos fields:
              "fields": {"nomeFornecedor": "Ligar", "descricao": "fio", "valor": 75.26,
                         "dataVencimento": "2023-06-25", "dataPagamento": "2025-06-25",
                         "formaPagamento": "pix"},
              "missing": [], "shouldAsk": False}
    await commands._tratar_parse(m, store, _client(), parsed)
    joined = " ".join(m.replies)
    assert "CONFIRMAR" in joined
    assert f"{ano}-06-25" in joined        # vencimento com ano atual
    assert "Pago em" not in joined         # PENDENTE: sem data de pagamento (sem vazamento)
    assert "2025" not in joined            # nada do ano alucinado
    assert "Forma:" not in joined          # PENDENTE: sem forma de pagamento
    assert "pendente" in joined.lower()    # rótulo "Conta a pagar (pendente)"
    d = store.list_active(UID)[0]
    assert d.intent == "criar_conta_pagar"
    assert "dataPagamento" not in (d.payload_extraido or {})


# ── pergunta de slot-fill não duplica ──────────────────────────────────────
def test_sem_pergunta_final_remove_so_a_pergunta():
    assert commands._sem_pergunta_final("Vou anotar a areia. Qual o valor?") == "Vou anotar a areia."
    assert commands._sem_pergunta_final("Calculei 650.") == "Calculei 650."
    assert commands._sem_pergunta_final("Qual o valor?") == ""


def test_montar_pergunta_uma_vez():
    msg = commands._montar_pergunta(
        "Ok, vou anotar a areia. Qual o valor?", "Qual o valor?", "(rascunho #1)")
    assert msg.count("Qual o valor?") == 1
    assert "Ok, vou anotar a areia." in msg  # narração preservada (sem a pergunta)


async def test_fluxo_slot_fill_nao_duplica_pergunta(tmp_path):
    _yaml(tmp_path)
    store = DraftStore(tmp_path / "r.db")
    m = FakeMsg("anotar uma areia para imperio das areias para o dia 26/06/26")
    parsed = {"reply": "Ok, vou anotar a areia para Império das Areias com vencimento "
                       "26/06/2026. Qual o valor?",
              "intent": "criar_conta_pagar",
              "fields": {"nomeFornecedor": "Imperio das Areias", "descricao": "areia",
                         "dataVencimento": "2026-06-26"},
              "missing": ["valor"], "shouldAsk": True, "question": "Qual o valor?"}
    await commands._tratar_parse(m, store, _client("Imperio das Areias", 49), parsed)
    joined = " ".join(m.replies)
    assert joined.count("Qual o valor?") == 1     # pergunta única


async def test_calculo_mantem_narracao_e_pergunta(tmp_path):
    """Quando a narração NÃO é uma pergunta (ex.: cálculo), ela é preservada + a pergunta."""
    _yaml(tmp_path)
    store = DraftStore(tmp_path / "r.db")
    m = FakeMsg("soma 325+325 e adiciona no Vanderli")
    parsed = {"reply": "Calculei 325+325=650 para Vanderli.", "intent": "criar_lancamento_rh",
              "fields": {"nomeFuncionario": "Vanderli", "valorUnit": 650, "destino": None},
              "missing": ["destino"], "shouldAsk": True, "question": "Vale ou pagamento?"}
    await commands._tratar_parse(m, store, _client("Vanderli", 10), parsed)
    joined = " ".join(m.replies)
    assert "650" in joined and "agamento" in joined.lower()
