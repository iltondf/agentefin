from financebot import config as cfgmod
from financebot.bot import AccessMiddleware


class _User:
    def __init__(self, uid):
        self.id = uid


async def test_denies_unknown_user(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "allowed_user_ids", "")
    mw = AccessMiddleware()
    called = {"v": False}

    async def handler(_e, _d):
        called["v"] = True

    res = await mw(handler, object(), {"event_from_user": _User(999)})
    assert res is None
    assert called["v"] is False


async def test_allows_listed_user(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "allowed_user_ids", "123")
    mw = AccessMiddleware()
    called = {"v": False}

    async def handler(_e, _d):
        called["v"] = True

    await mw(handler, object(), {"event_from_user": _User(123)})
    assert called["v"] is True


async def test_rate_limit(monkeypatch):
    monkeypatch.setattr(cfgmod.settings, "allowed_user_ids", "123")
    monkeypatch.setattr(cfgmod.settings, "rate_limit_per_min", 2)
    mw = AccessMiddleware()
    calls = []

    async def handler(_e, _d):
        calls.append(1)

    user = _User(123)
    await mw(handler, object(), {"event_from_user": user})
    await mw(handler, object(), {"event_from_user": user})
    await mw(handler, object(), {"event_from_user": user})  # 3ª: bloqueada
    assert len(calls) == 2
