"""Garante o formato da chamada LLM (sem rede real) e o parse do retorno."""
import httpx
import pytest

from financebot import parser, config as cfgmod


async def test_parser_monta_request_e_parseia(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "llm_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "openrouter_api_key", "sk-or-test")
    monkeypatch.setattr(cfgmod.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(cfgmod.settings, "llm_model", "")  # usa fallback

    captured = {}

    class FakeResp:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content":
                '{"intent":"criar_lancamento_rh","confidence":0.9,'
                '"fields":{"nomeFuncionario":"Vanderli","tipo":"diaria_extra",'
                '"destino":"pagamento","qtd":2,"valorUnit":120,"data":"hoje"},'
                '"missing":[],"shouldAsk":false,"question":null}'}}]}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["model"] = json["model"]
            captured["auth"] = headers["Authorization"]
            captured["json_mode"] = json.get("response_format", {}).get("type")
            return FakeResp()

    monkeypatch.setattr(parser.httpx, "AsyncClient", FakeClient)
    out = await parser.parse("Vanderli fez duas diárias de R$120 no pagamento")
    assert out["intent"] == "criar_lancamento_rh"
    assert out["fields"]["qtd"] == 2 and out["fields"]["valorUnit"] == 120
    assert captured["model"] == "openai/gpt-4o-mini"     # fallback aplicado
    assert captured["auth"] == "Bearer sk-or-test"        # usa OPENROUTER_API_KEY
    assert captured["json_mode"] == "json_object"
    assert captured["url"].endswith("/chat/completions")


async def test_parser_off_retorna_none(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "llm_enabled", False)
    assert await parser.parse("qualquer coisa") is None
