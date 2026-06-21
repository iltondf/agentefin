"""Integração real over-the-wire: cliente HTTP contra um servidor stub local
que devolve o MESMO envelope da API de agentes do BRGlobal.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from financebot import formatters as fmt
from financebot.client import FinanceClient

_PAYLOAD = {
    "apiVersion": "v1",
    "generatedAt": "2026-05-30T00:00:00.000Z",
    "environment": "test",
    "data": {
        "total": 1,
        "referencia": "2026-05-30",
        "data": [
            {
                "id": 1,
                "fornecedorNome": "Energia SA",
                "saldoAberto": 150.0,
                "dataVencimento": "2026-05-30",
                "descricao": "Conta de luz",
            }
        ],
    },
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(_PAYLOAD).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_a):  # silencia o log do http.server
        pass


@pytest.fixture
def base_url():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}/api/agent/v1"
    finally:
        srv.shutdown()


async def test_end_to_end_real_http(base_url):
    client = FinanceClient(base_url=base_url, read_key="k")
    data = await client.contas_pagar_hoje()
    texto = fmt.hoje(data)
    assert "Energia SA" in texto
    assert "R$ 150,00" in texto
    assert "Conta de luz" in texto
