import pytest

from financebot.client import FinanceClient


@pytest.fixture(autouse=True)
def _fast_backoff(monkeypatch):
    """Neutraliza o backoff de retry para os testes rodarem instantâneos."""
    async def _noop(_attempt):
        return None

    monkeypatch.setattr(FinanceClient, "_backoff", staticmethod(_noop))
