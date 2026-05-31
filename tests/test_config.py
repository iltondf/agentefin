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


def test_default_conta_empty_string_to_none():
    # `.env.example` copiado as-is traz DEFAULT_CONTA_BANCARIA_ID= (vazio).
    assert Settings(default_conta_bancaria_id="").default_conta_bancaria_id is None
    assert Settings(default_conta_bancaria_id="   ").default_conta_bancaria_id is None
    assert Settings(default_conta_bancaria_id="5").default_conta_bancaria_id == 5
