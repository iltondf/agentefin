from financebot.config import Settings


def test_allowed_ids_parsing():
    s = Settings(allowed_user_ids="1, 2 ,abc,3,")
    assert s.allowed_ids == {1, 2, 3}


def test_allowed_ids_empty_denies_all():
    s = Settings(allowed_user_ids="")
    assert s.allowed_ids == set()


def test_defaults_llm_off():
    s = Settings()
    assert s.llm_enabled is False
