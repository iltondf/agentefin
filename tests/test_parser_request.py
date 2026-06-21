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


async def test_parser_fallback_modelo_invalido(monkeypatch):
    """1º modelo retorna 400 (id inválido) → tenta o próximo → sucesso."""
    monkeypatch.setattr(cfgmod.settings, "llm_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "openrouter_api_key", "sk-or-test")
    monkeypatch.setattr(cfgmod.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(cfgmod.settings, "llm_model", "deepseek/deepseek-v4-flash")

    tentativas = []

    class FakeResp:
        def __init__(self, status, content=None):
            self.status_code = status
            self.text = "not a valid model id" if status != 200 else "ok"
            self._content = content
        def json(self):
            return {"choices": [{"message": {"content": self._content}}]}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, headers=None):
            tentativas.append(json["model"])
            if json["model"] == "deepseek/deepseek-v4-flash":
                return FakeResp(400)
            return FakeResp(200, '{"intent":"conversa","reply":"oi","fields":{}}')

    monkeypatch.setattr(parser.httpx, "AsyncClient", FakeClient)
    out = await parser.parse("oi")
    assert out["intent"] == "conversa"
    assert tentativas[0] == "deepseek/deepseek-v4-flash"   # tentou o configurado
    assert len(tentativas) >= 2                             # caiu para o fallback


async def test_parser_envia_headers_openrouter(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "llm_enabled", True)
    monkeypatch.setattr(cfgmod.settings, "openrouter_api_key", "sk-or-test")
    monkeypatch.setattr(cfgmod.settings, "llm_model", "x/y")
    cap = {}

    class FakeResp:
        status_code = 200
        text = "ok"
        def json(self): return {"choices": [{"message": {"content": '{"intent":"conversa"}'}}]}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, headers=None):
            cap["headers"] = headers
            return FakeResp()

    monkeypatch.setattr(parser.httpx, "AsyncClient", FakeClient)
    await parser.parse("oi")
    assert cap["headers"]["Authorization"] == "Bearer sk-or-test"
    assert "X-Title" in cap["headers"]
