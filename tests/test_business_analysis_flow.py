import pandas as pd
import pytest
from test_conversational_analysis import DirectorProvider
from test_gender_purchase_comparison import purchases
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision, AnalysisQuestion
from app.knowledge.knowledge_service import KnowledgeService

QUESTIONS = [
    ("Quais são os dias da semana com maior faturamento e quantidade de compras?", "weekday"),
    ("Qual é a frequência média de compras por cliente durante uma campanha?", "frequency"),
    (
        "Qual percentual do faturamento é gerado pelos 10% de clientes que mais gastam?",
        "concentration",
    ),
    ("Como o ticket médio evolui ao longo de uma campanha promocional?", "ticket_evolution"),
    (
        "Qual faixa etária apresenta maior ticket médio e maior frequência de compras?",
        "age_metrics",
    ),
    (
        "Existem diferenças significativas no comportamento de compra entre homens e mulheres?",
        "gender",
    ),
    (
        "Qual percentual dos clientes realiza apenas uma compra "
        "e qual percentual realiza múltiplas compras?",
        "purchase_repeat",
    ),
    ("Quais segmentos de lojas são mais consumidos por cada faixa etária?", "age_segments"),
    (
        "Quais bairros e cidades concentram o maior número de clientes e o maior faturamento?",
        "geo_ranking",
    ),
    ("Quais regiões apresentam clientes com maior ticket médio?", "geo_ticket"),
    (
        "Qual percentual dos clientes participantes reside fora da cidade "
        "onde está localizado o shopping?",
        "outside_city",
    ),
    ("Quais bairros apresentam maior frequência de compras por cliente?", "neighborhood_frequency"),
    (
        "Quais segmentos representam a maior participação no faturamento "
        "e na quantidade de compras?",
        "segment_share",
    ),
    ("Quais lojas possuem maior capacidade de atrair clientes únicos?", "store_customers"),
    (
        "Quais segmentos possuem os maiores tickets médios "
        "e quais possuem maior recorrência de compras?",
        "segment_recurrence",
    ),
    ("Quais combinações de segmentos são mais consumidas pelos mesmos clientes?", "segment_pairs"),
    (
        "Quais campanhas apresentam maior faturamento, quantidade de compras e clientes únicos?",
        "campaign_ranking",
    ),
    (
        "Em quais campanhas os consumidores apresentam maior frequência de compras "
        "e ticket médio por cliente?",
        "campaign_frequency",
    ),
    (
        "Como evolui a participação dos clientes ao longo de cada campanha, "
        "considerando início, meio e fim?",
        "campaign_phases",
    ),
    (
        "Qual percentual de clientes participa de mais de uma campanha "
        "e como seu comportamento de consumo evolui entre elas?",
        "campaign_retention",
    ),
]


@pytest.mark.parametrize("question,monthly", [
    ("qual a frequencia de compras por shopping?", False),
    ("qual a frequencia de compras por pessoa por mês aberta por shopping?", True),
    ("quantas compras por clientes tem cada shopping?", False),
])
def test_customer_frequency_by_shopping_and_month(question, monthly):
    frame = business_frame().iloc[:6].copy()
    frame["cd_compra"] = [str(i) for i in range(6)]
    frame["sk_cliente"] = ["a", "a", "b", "a", "a", None]
    frame["nm_empreendimento"] = ["Shopping A"] * 4 + ["Shopping B"] * 2
    frame["dt_registro_mos"] = ["2026-05-01"] * 3 + ["2026-06-01"] * 3
    response = service(frame=frame).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
    )
    assert response.metadata.get("business_analysis", {}).get("mode") == "frequency"
    rows = {(row.get("mes"), row["nm_empreendimento"]): row for row in response.data}
    if monthly:
        assert set(rows) == {("2026-05", "Shopping A"), ("2026-06", "Shopping A"),
                             ("2026-06", "Shopping B")}
        assert rows[("2026-05", "Shopping A")]["frequencia_media"] == 1.5
        assert rows[("2026-06", "Shopping A")]["frequencia_media"] == 1
    else:
        assert set(rows) == {(None, "Shopping A"), (None, "Shopping B")}
        assert rows[(None, "Shopping A")]["frequencia_media"] == 2
    assert rows[("2026-06" if monthly else None, "Shopping B")]["frequencia_media"] == 1
    assert "Compras por cliente" in response.answer


def business_frame():
    first = purchases()
    first["dt_nascimento"] = ["1990-01-01" if i % 2 else "2005-01-01" for i in range(len(first))]
    first["nm_segmento"] = ["Moda" if i % 2 else "Alimentação" for i in range(len(first))]
    first["nm_fantasa"] = first.nm_segmento + " Loja"
    first["cidade"] = "Goiânia"
    first["bairro"] = "Centro"
    first["uf"] = "GO"
    second = first.copy()
    second["nm_promocao"] = "Promoção Pais 2026"
    second["cd_promocao"] = "p2"
    second["cd_compra"] += "-later"
    second["dt_registro_mos"] = "2026-08-10"
    second["sk_dtinicio"] = 20260801
    second["sk_dtfim"] = 20260831
    return pd.concat([first, second], ignore_index=True)


@pytest.mark.parametrize("question", [
    "qual promoção teve a maior representatividade no BUR?",
    "qual foi a melhor promoção que ocorreu no BUR?",
])
def test_campaign_performance_question_does_not_depend_on_model_or_previous_winner(question):
    frame = business_frame().iloc[:4].copy()
    frame["cd_compra"] = ["a", "b", "c", "d"]
    frame["cd_promocao"] = ["p1", "p1", "p1", "p2"]
    frame["nm_promocao"] = ["Volume"] * 3 + ["Receita"]
    frame["vl_compra"] = [10, 10, 10, 90]
    other = frame.copy()
    other["nm_empreendimento"] = "Shopping Sul"
    other["vl_compra"] = 10000
    provider = DirectorProvider(AnalysisDecision(
        clarification="A análise anterior não retornou dados",
    ))
    instance = service(provider, pd.concat([frame, other], ignore_index=True))
    for _ in range(2):
        response = instance.execute_question(
            question=question, knowledge_context=KnowledgeService().get_context(),
            session_id="campaign-performance",
        )
        assert {row["nm_empreendimento"] for row in response.data} == {"Buriti Shopping"}
        if "representatividade" in question:
            assert response.metadata.get("business_analysis", {}).get("mode") == "campaign_ranking"
            assert {row["nm_promocao"] for row in response.data} == {"Volume", "Receita"}
            assert "Maior faturamento: Receita" in response.answer
            assert "Maior compras: Volume" in response.answer
            rows = {row["nm_promocao"]: row for row in response.data}
            assert rows["Volume"]["participacao_compras_pct"] == 75
            assert rows["Receita"]["participacao_faturamento_pct"] == 75
        else:
            assert len(response.data) == 1
            assert response.data[0]["nm_promocao"] == "Receita"
            assert "faturamento" in response.answer


@pytest.mark.parametrize("criterion,expected", [("compras", "Volume"),
                                              ("faturamento", "Receita")])
def test_campaign_share_uses_requested_metric_and_denominator_before_limit(criterion, expected):
    frame = business_frame().iloc[:4].copy()
    frame["cd_compra"] = ["a", "b", "c", "d"]
    frame["cd_promocao"] = ["p1", "p1", "p1", "p2"]
    frame["nm_promocao"] = ["Volume"] * 3 + ["Receita"]
    frame["vl_compra"] = [10, 10, 10, 90]
    unassigned = frame.iloc[[0]].copy()
    unassigned["cd_compra"] = "unassigned"
    unassigned["cd_promocao"] = None
    unassigned["nm_promocao"] = None
    unassigned["vl_compra"] = 9999
    response = service(frame=pd.concat([frame, unassigned], ignore_index=True)).execute_question(
        question=f"Qual promoção teve maior representatividade em {criterion} no BUR? Top 1",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(response.data) == 1
    row = response.data[0]
    assert row["nm_promocao"] == expected
    assert row[f"participacao_{criterion}_pct"] == 75


@pytest.mark.parametrize("question,mode", QUESTIONS)
def test_all_twenty_questions_have_deterministic_supported_routes(question, mode):
    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(
                    title="Wrong",
                    question="Qual o faturamento da campanha No Pelo 360?",
                )
            ]
        )
    )
    response = service(provider, business_frame()).execute_question(
        question=question,
        knowledge_context=KnowledgeService().get_context(),
        session_id="twenty",
    )
    if mode == "gender":
        assert "gender_comparison" in response.metadata
    else:
        assert response.metadata.get("business_analysis", {}).get("mode") == mode, response.answer
    assert response.data, response.answer
    assert response.model_dump_json()
    assert "No Pelo" not in response.answer
    assert not any("sk_cliente" in row or "__purchase" in row for row in response.data)


def test_weekday_scope_and_dedup_do_not_leak_another_campaign():
    frame = business_frame()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    response = service(frame=frame).execute_question(
        question=QUESTIONS[0][0] + " Na promoção mães 2026 do Buriti Shopping.",
        knowledge_context=KnowledgeService().get_context(),
    )
    expected = frame[frame.cd_promocao.eq("13718")].drop_duplicates("cd_compra")
    assert sum(row["quantidade_compras"] for row in response.data) == len(expected)
    assert sum(row["faturamento"] for row in response.data) == expected.vl_compra.sum()
    assert "Mães E Namorados 2026" in response.answer


def test_outside_city_without_shopping_city_does_not_invent_a_location():
    frame = business_frame()
    frame["nm_empreendimento"] = "Shopping sem cadastro"
    response = service(frame=frame).execute_question(
        question=QUESTIONS[10][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert "cidade do shopping" in response.answer.lower()
    assert all(row.get("status") == "missing_shopping_city" for row in response.data)


def test_outside_city_uses_the_user_supplied_shopping_municipality():
    frame = business_frame()
    frame.loc[frame.sk_cliente.eq("F0"), "cidade"] = "Aparecida de Goiânia"
    response = service(frame=frame).execute_question(
        question=QUESTIONS[10][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(response.data) == 1
    assert response.data[0]["cidade_shopping"] == "Aparecida de Goiânia"
    assert response.data[0]["proporcao_fora_cidade_conhecida"] == pytest.approx(47 / 48)


def test_missing_required_age_data_is_explained():
    response = service(frame=business_frame().drop(columns="dt_nascimento")).execute_question(
        question=QUESTIONS[4][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert "dt_nascimento" in response.answer or "nascimento" in response.answer.lower()


def test_neighborhood_frequency_is_prominent_and_present_in_every_row():
    base = business_frame().iloc[[0]].copy()
    rows = []
    for neighborhood, purchase_count in [("Loteamento Morada dos Sonhos", 102),
                                     ("Campos Elíseos", 14)]:
        for index in range(purchase_count):
            row = base.copy()
            row["bairro"] = neighborhood
            row["sk_cliente"] = neighborhood
            row["cd_compra"] = f"{neighborhood}-{index}"
            rows.append(row)
    response = service(frame=pd.concat(rows, ignore_index=True)).execute_question(
        question="Quais bairros apresentam maior frequência de compras por cliente?",
        knowledge_context=KnowledgeService().get_context(),
    )
    by_neighborhood = {row["bairro"]: row for row in response.data}
    assert by_neighborhood["Campos Elíseos"]["frequencia_media"] == 14
    assert "102,00 compras por cliente" in response.answer
    table = [line for line in response.answer.splitlines() if line.startswith("|")]
    headers = [cell.strip() for cell in table[0].strip("|").split("|")]
    frequency = headers.index("Compras por cliente")
    assert frequency == headers.index("Bairro") + 1
    last = [cell.strip() for cell in table[-1].strip("|").split("|")]
    assert last[frequency] == "14,00"


@pytest.mark.parametrize("question,expected", [
    ("Quais segmentos de lojas são mais consumidos por cada faixa etária?", 5),
    ("Qual top 3 de segmentos de lojas são mais consumidos por cada faixa etária?", 3),
    ("Quais segmentos de lojas são mais consumidos por cada faixa etária? Limite a 2.", 2),
    ("Quais segmentos de lojas são mais consumidos por cada faixa etária? Mostre apenas 1.", 1),
    ("Quais segmentos de lojas são mais consumidos por cada faixa etária? Limite de 4.", 4),
    ("Quais segmentos de lojas são mais consumidos por cada faixa etária? Mostre 2.", 2),
])
def test_age_segment_question_honors_only_requested_limits(question, expected):
    frame = business_frame().iloc[:10].copy().drop(columns="dt_nascimento")
    frame["sk_cliente"] = [f"client-{i}" for i in range(10)]
    frame["cd_compra"] = [f"purchase-{i}" for i in range(10)]
    frame["faixa_etaria"] = ["18-24"] * 5 + ["60+"] * 5
    frame["nm_segmento"] = ["A", "B", "C", "D", "E"] * 2
    response = service(frame=frame).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
    )
    counts = pd.DataFrame(response.data).groupby("faixa_etaria").size().to_dict()
    assert counts == {"18-24": expected, "60+": expected}


@pytest.mark.parametrize("index", [0, 1, 16, 17, 18, 19])
def test_explicit_year_never_includes_purchases_from_another_year(index):
    response = service(frame=business_frame()).execute_question(
        question=QUESTIONS[index][0] + " Em 2025.",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == [], response.answer


def test_explicit_store_segment_filter_is_not_discarded():
    response = service(frame=business_frame()).execute_question(
        question="Qual é a frequência média de compras por cliente no segmento Moda?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(response.data) == 1
    assert response.data[0]["quantidade_compras"] == 96
    assert response.data[0]["frequencia_media"] == pytest.approx(3)


def test_independent_ticket_and_frequency_leaders_are_reported_separately():
    frame = business_frame().iloc[:4].copy()
    frame["cd_compra"] = ["1", "2", "3", "4"]
    frame["sk_cliente"] = ["a", "a", "b", "c"]
    frame["nm_segmento"] = ["Moda", "Moda", "Moda", "Alimentação"]
    frame["vl_compra"] = [10, 10, 10, 100]
    response = service(frame=frame).execute_question(
        question=QUESTIONS[14][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert "Maior ticket por compra: Alimentação" in response.answer
    assert "Maior frequência: Moda" in response.answer


def test_multicampaign_denominator_excludes_unassigned_receipts():
    frame = business_frame()
    outside = frame.iloc[[0]].copy()
    outside["cd_compra"] = "unassigned"
    outside["sk_cliente"] = "unassigned"
    outside["cd_promocao"] = None
    outside["nm_promocao"] = None
    response = service(frame=pd.concat([frame, outside], ignore_index=True)).execute_question(
        question=QUESTIONS[19][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert all(row["denominador_clientes"] == 48 for row in response.data)
    assert len(response.data) == 2


def test_unknown_shopping_suffix_does_not_fall_back_to_the_base_shopping():
    response = service(frame=business_frame()).execute_question(
        question=QUESTIONS[0][0] + " No Buriti Shopping X.",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == []


def test_campaign_can_be_selected_by_its_exact_identifier():
    response = service(frame=business_frame()).execute_question(
        question=QUESTIONS[0][0] + " Na campanha 13718 do Buriti Shopping.",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data, response.answer
    assert sum(row["quantidade_compras"] for row in response.data) == 96


@pytest.mark.parametrize(
    "shopping,state,city",
    [
        ("Buriti shopping", "GO", "Aparecida de Goiânia"),
        ("Portal Shopping", "GO", "Goiânia"),
        ("Águas Lindas Shopping", "GO", "Águas Lindas de Goiás"),
        ("Brasil Park Shopping", "GO", "Anápolis"),
        ("Shopping Sul", "GO", "Valparaíso de Goiás"),
        ("Buriti Shopping Rio Verde", "GO", "Rio Verde"),
        ("Buriti Shopping Mogi Guaçu", "SP", "Mogi-Guaçu"),
        ("Buriti Shopping Guará", "SP", "Guaratinguetá"),
    ],
)
def test_all_eight_supplied_shopping_municipalities_are_used(shopping, state, city):
    frame = business_frame().iloc[:2].copy()
    frame["nm_empreendimento"] = shopping
    frame["uf"] = state
    frame["cidade"] = [city, "Outra cidade"]
    result = service(frame=frame).execute_question(
        question=QUESTIONS[10][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data[0]["cidade_shopping"] == city
    assert result.data[0]["uf_shopping"] == state
    assert result.data[0]["proporcao_fora_cidade_conhecida"] == 0.5


def test_residence_with_missing_state_is_not_treated_as_known():
    frame = business_frame().iloc[:2].copy()
    frame["uf"] = None
    result = service(frame=frame).execute_question(
        question=QUESTIONS[10][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data[0]["clientes_cidade_conhecida"] == 0
    assert result.data[0]["clientes_cidade_desconhecida"] == 2
    assert result.data[0]["proporcao_fora_cidade_conhecida"] is None


def test_normalized_display_variants_do_not_make_shopping_ambiguous():
    frame = business_frame()
    frame.loc[frame.index % 2 == 0, "nm_empreendimento"] = "BURITI SHOPPING"
    result = service(frame=frame).execute_question(
        question=QUESTIONS[0][0] + " No Buriti Shopping?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert sum(row["quantidade_compras"] for row in result.data) == len(frame)


def test_both_geographic_levels_are_present_when_table_is_limited():
    frame = business_frame().iloc[:105].copy()
    frame["bairro"] = [f"Bairro {i}" for i in range(len(frame))]
    result = service(frame=frame).execute_question(
        question=QUESTIONS[8][0],
        knowledge_context=KnowledgeService().get_context(),
    )
    assert "Cidade: Maior faturamento:" in result.answer
    assert "Bairro: Maior faturamento:" in result.answer
    assert "| cidade |" in result.answer.lower()


def test_global_aggregation_uses_only_authorized_shopping_source_rows():
    from app.governance.policy import DataGovernancePolicy

    frame = business_frame()
    outside = frame.copy()
    outside["nm_empreendimento"] = "Shopping Sul"
    outside["vl_compra"] = 999999
    instance = service(frame=pd.concat([frame, outside], ignore_index=True))
    instance._governance_policy = DataGovernancePolicy(allowed_shoppings={"Buriti Shopping"})
    result = instance.execute_question(
        question=QUESTIONS[2][0], knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data[0]["receita"] == frame.vl_compra.sum()
