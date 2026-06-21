from financebot.drafts import DraftStore


def _store(tmp_path):
    return DraftStore(tmp_path / "t.db")


def test_create_list_get(tmp_path):
    s = _store(tmp_path)
    assert s.available
    d = s.create(chat_id=1, user_id=42, texto="areia 1800", dominio="financeiro",
                 intent="criar_conta_pagar_paga", payload={"valor": 1800}, faltando=[])
    assert d.id > 0 and d.status == "aguardando_confirmacao"
    got = s.get(d.id)
    assert got.payload_extraido["valor"] == 1800
    assert len(s.list_active(42)) == 1
    assert s.list_active(999) == []


def test_create_pendente_quando_falta(tmp_path):
    s = _store(tmp_path)
    d = s.create(chat_id=1, user_id=42, texto="diaria", dominio="rh",
                 intent="criar_lancamento_rh", payload={}, faltando=["destino"])
    assert d.status == "pendente"
    assert d.campos_faltando == ["destino"]


def test_status_e_cancel(tmp_path):
    s = _store(tmp_path)
    d = s.create(chat_id=1, user_id=42, texto="x")
    s.set_status(d.id, "confirmado")
    assert s.get(d.id).status == "confirmado"
    s.set_status(d.id, "cancelado")
    assert s.list_active(42) == []  # cancelado não é ativo


def test_persistencia_reabre(tmp_path):
    s1 = _store(tmp_path)
    d = s1.create(chat_id=1, user_id=7, texto="persistente")
    s2 = DraftStore(tmp_path / "t.db")  # reabre o mesmo arquivo
    assert s2.get(d.id).texto_original == "persistente"


def test_update_payload(tmp_path):
    s = _store(tmp_path)
    d = s.create(chat_id=1, user_id=7, texto="x", payload={"a": 1})
    s.update(d.id, payload_extraido={"a": 1, "b": 2}, idempotency_key="tg:1:1:i:202606")
    got = s.get(d.id)
    assert got.payload_extraido["b"] == 2
    assert got.idempotency_key == "tg:1:1:i:202606"
