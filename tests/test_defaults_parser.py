from financebot import defaults
from financebot import parser
from financebot import config as cfgmod


def test_defaults_load_e_get(tmp_path):
    f = tmp_path / "d.yaml"
    f.write_text(
        "obraPadraoId: 4\nformaPagamentoPadrao: pix\n"
        "rh:\n  destinoPadrao: pagamento\ncategorias:\n  areia: 16\n",
        encoding="utf-8",
    )
    defaults.load_defaults(f)
    assert defaults.get("obraPadraoId") == 4
    assert defaults.get("rh.destinoPadrao") == "pagamento"
    assert defaults.get("inexistente", "x") == "x"
    assert defaults.categoria_por_palavra("comprei AREIA hoje") == 16
    assert defaults.categoria_por_palavra("comprei cimento") is None


def test_defaults_ausente_nao_quebra(tmp_path):
    defaults.load_defaults(tmp_path / "nao_existe.yaml")
    assert defaults.get("qualquer") is None


def test_parser_desligado_por_padrao(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "llm_enabled", False)
    assert parser.is_enabled() is False


def test_parser_safe_json_extrai_bloco():
    obj = parser._safe_json('```json\n{"intent":"criar_conta_pagar","confidence":0.8}\n```')
    assert obj["intent"] == "criar_conta_pagar"
    obj2 = parser._safe_json('lixo antes {"intent":"x"} lixo depois')
    assert obj2["intent"] == "x"
    assert parser._safe_json("sem json aqui") is None


def test_write_intents_whitelist():
    assert "criar_lancamento_rh" in parser.WRITE_INTENTS
    assert "rm -rf" not in parser.WRITE_INTENTS
