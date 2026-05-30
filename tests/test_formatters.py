from financebot import formatters as fmt


def test_brl():
    assert fmt.brl(1234.5) == "R$ 1.234,50"
    assert fmt.brl("0") == "R$ 0,00"
    assert fmt.brl(None) == "R$ 0,00"
    assert fmt.brl(1000000) == "R$ 1.000.000,00"


def test_data_br():
    assert fmt.data_br("2026-05-30T12:00:00.000Z") == "30/05/2026"
    assert fmt.data_br("2026-05-30") == "30/05/2026"
    assert fmt.data_br(None) == "—"
    assert fmt.data_br("") == "—"


def test_lista_contas_vazia():
    out = fmt.hoje({"data": [], "total": 0})
    assert "Nenhuma conta" in out


def test_lista_contas_com_itens():
    obj = {
        "total": 2,
        "data": [
            {"id": 10, "fornecedorNome": "Energia SA", "saldoAberto": 150.0,
             "dataVencimento": "2026-05-30", "descricao": "Conta de luz"},
            {"id": 11, "fornecedorNome": "Agua SA", "saldoAberto": 80.5,
             "dataVencimento": "2026-05-30", "dadosPagamentoPendentes": True},
        ],
    }
    out = fmt.hoje(obj)
    assert "Energia SA" in out
    assert "R$ 150,00" in out
    assert "#11" in out
    assert "sem código de pagamento" in out
    assert "R$ 230,50" in out  # soma da amostra


def test_criticas_com_recomendacao():
    obj = {"total": 1, "data": [
        {"id": 5, "fornecedorNome": "Fornecedor X", "saldoAberto": 999.0,
         "dataVencimento": "2026-06-01", "prioridade": "critica",
         "recomendacao": "Pagar HOJE."},
    ]}
    out = fmt.criticas(obj)
    assert "CRITICA" in out
    assert "Pagar HOJE." in out


def test_resumo():
    obj = {
        "referencia": "2026-05-30",
        "contasPagar": {
            "vencidas": {"total": 3, "valorTotal": 300},
            "hoje": {"total": 1, "valorTotal": 100},
            "proximos7Dias": {"total": 5, "valorTotal": 500},
            "dadosPagamentoPendentes": 2,
        },
    }
    out = fmt.resumo(obj)
    assert "RESUMO DIÁRIO" in out
    assert "R$ 300,00" in out
    assert "Sem código de pagamento: 2" in out


def test_painel_caixa_null_e_observacoes():
    obj = {
        "referencia": {"hoje": "2026-05-30", "mes": "2026-05"},
        "contasPagar": {
            "vencidas": {"total": 1, "valorTotalAberto": 100},
            "hoje": {"total": 0, "valorTotalAberto": 0},
            "proximos7Dias": {"total": 2, "valorTotalAberto": 200},
            "criticas": {"total": 1},
            "dadosPagamentoPendentes": 0,
        },
        "caixa": None,
        "matches": {"fortes": 1, "provaveis": 2},
        "sugestoes": {"pendentes": 3},
        "_observacoes": ["contaBancariaId não informada"],
    }
    out = fmt.painel(obj)
    assert "PAINEL OPERACIONAL" in out
    assert "Vencidas: 1" in out
    assert "matches fortes 1" in out
    assert "contaBancariaId não informada" in out


def test_whoami():
    obj = {"apiKey": {"nome": "bot", "prefixo": "bgf_test_abc", "escopos": ["read:financeiro"]},
           "serverTime": "2026-05-30T00:00:00Z"}
    out = fmt.whoami(obj)
    assert "read:financeiro" in out
    assert "bot" in out
