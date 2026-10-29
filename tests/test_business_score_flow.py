import pandas as pd
import pytest
from test_conversational_analysis import DirectorProvider
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision
from app.knowledge.knowledge_service import KnowledgeService


def receipts():
    return pd.DataFrame([
        {
            "nm_empreendimento": "Buriti Shopping", "cd_empreendimento": "bur",
            "nm_fantasa": store, "sk_loja": store,
            "sk_cliente": f"internal-client-{store}", "cd_compra": f"{store}-{i}",
            "vl_compra": value, "dt_registro_mos": "2026-05-10",
            "nm_promocao": "Promoção Mães 2026", "cd_promocao": "m2026",
            "uf": "GO", "cidade": "Goiânia", "bairro": f"Bairro {store}",
        }
        for store, count, value in [("A", 4, 25), ("B", 2, 60), ("C", 1, 200)]
        for i in range(count)
    ])


def ask(question, frame=None):
    provider = DirectorProvider(AnalysisDecision(clarification="Não deveria depender do modelo"))
    return service(provider, receipts() if frame is None else frame).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
        session_id="score",
    )


@pytest.mark.parametrize("question,entity", [
    ("Qual loja foi mais representativa no BUR?", "loja"),
    ("Qual cliente mais engajado no BUR?", "cliente"),
    ("Qual bairro teve maior representatividade no BUR?", "bairro"),
])
def test_open_questions_use_explainable_score_without_model_rewrite(question, entity):
    response = ask(question)
    assert response.metadata.get("business_analysis", {}).get("mode") == "entity_ranking"
    assert len(response.data) == 3, response.answer
    assert response.data[0]["score"] == pytest.approx(200 / 3)
    assert response.metadata["business_analysis"]["score"]["population"] == 3
    assert "percentis" in response.answer
    assert "pesos iguais" in response.answer
    assert "Score" in response.answer
    assert all("sk_cliente" not in row and "sk_loja" not in row for row in response.data)
    if entity == "cliente":
        assert "internal-client" not in response.model_dump_json()
        assert all(row["cliente"].startswith("Cliente ") for row in response.data)


def test_top_limit_is_applied_after_score_and_without_changing_percentiles():
    full = ask("Quais lojas foram mais representativas no BUR?")
    top = ask("Top 2 lojas mais representativas no BUR")
    assert len(top.data) == 2
    assert top.data == full.data[:2]
    assert top.metadata["business_analysis"]["score"]["population"] == 3


@pytest.mark.parametrize("criterion,expected", [
    ("faturamento", "C"), ("quantidade de compras", "A"), ("ticket médio", "C"),
])
def test_explicit_criterion_overrides_implicit_score(criterion, expected):
    response = ask(f"Qual loja foi mais representativa em {criterion} no BUR?")
    assert response.data, response.answer
    assert response.data[0]["nm_fantasa"] == expected
    assert all("score" not in row for row in response.data)


def test_source_scope_and_duplicate_receipts_precede_percentiles():
    frame = receipts()
    outside = frame.copy()
    outside["nm_empreendimento"] = "Shopping Sul"
    outside["cd_empreendimento"] = "sul"
    outside["vl_compra"] = 999999
    previous = frame.copy()
    previous["dt_registro_mos"] = "2025-05-10"
    previous["cd_compra"] += "-old"
    response = ask("Qual loja foi mais representativa no BUR em 2026?", pd.concat([
        frame, outside, previous, frame.iloc[[0]],
    ], ignore_index=True))
    assert {row["nm_empreendimento"] for row in response.data} == {"Buriti Shopping"}
    assert sum(row["quantidade_compras"] for row in response.data) == 7
    assert response.data[0]["score"] == pytest.approx(200 / 3)


def test_single_candidate_reports_score_unavailable_instead_of_winner():
    response = ask("Qual loja foi mais representativa no BUR?", receipts().iloc[:4])
    assert len(response.data) == 1
    assert response.data[0]["score"] is None
    assert "apenas uma" in response.answer.lower()
    assert "Maior score" not in response.answer


def test_knowledge_context_documents_score_and_explicit_metric_precedence():
    knowledge = KnowledgeService().get_context()
    assert any(metric.name == "score" for metric in knowledge.metrics)
    rule = next(rule for rule in knowledge.rules if rule.code == "purchasing_percentile_score")
    assert "Métrica explícita prevalece" in rule.description


def test_missing_client_is_excluded_from_customer_score_only():
    frame = receipts()
    frame.loc[frame.nm_fantasa.eq("C"), "sk_cliente"] = None
    customers = ask("Qual cliente mais engajado no BUR?", frame)
    assert len(customers.data) == 2
    assert customers.metadata["business_analysis"]["score"]["population"] == 2
    stores = ask("Qual loja foi mais representativa no BUR?", frame)
    assert stores.metadata["business_analysis"]["score"]["population"] == 2


def test_empty_period_does_not_invent_a_score():
    response = ask("Qual loja foi mais representativa no BUR em 2020?")
    assert response.data == []


def test_authorized_shopping_scope_precedes_score_population():
    from app.governance.policy import DataGovernancePolicy

    frame = receipts()
    outside = frame.copy()
    outside["nm_empreendimento"] = "Shopping Sul"
    outside["cd_empreendimento"] = "sul"
    outside["vl_compra"] = 999999
    instance = service(frame=pd.concat([frame, outside], ignore_index=True))
    instance._governance_policy = DataGovernancePolicy(allowed_shoppings={"Buriti Shopping"})
    response = instance.execute_question(
        question="Quais lojas foram mais representativas?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(response.data) == 3
    assert response.metadata["business_analysis"]["score"]["population"] == 3
    assert {row["nm_empreendimento"] for row in response.data} == {"Buriti Shopping"}


def test_same_store_name_in_different_shoppings_is_not_merged():
    frame = receipts()
    other = frame.iloc[[0]].copy()
    other["nm_empreendimento"] = "Shopping Sul"
    other["cd_empreendimento"] = "sul"
    response = ask("Quais lojas foram mais representativas?", pd.concat([frame, other]))
    assert len(response.data) == 4
    assert len([row for row in response.data if row["nm_fantasa"] == "A"]) == 2


def test_bairro_names_in_different_cities_are_not_merged():
    frame = receipts()
    frame["bairro"] = "Centro"
    frame["cidade"] = frame.nm_fantasa.map({"A": "Cidade A", "B": "Cidade B", "C": "Cidade C"})
    response = ask("Quais bairros foram mais representativos?", frame)
    assert len(response.data) == 3
    assert {row["cidade"] for row in response.data} == {"Cidade A", "Cidade B", "Cidade C"}


def test_suppressed_groups_do_not_influence_percentiles_or_take_top_positions():
    from app.governance.policy import DataGovernancePolicy

    frame = receipts()
    frame["sk_cliente"] = [f"person-{i}" for i in range(len(frame))]
    instance = service(frame=frame)
    instance._governance_policy = DataGovernancePolicy(minimum_group_size=2)
    response = instance.execute_question(
        question="Top 1 lojas mais representativas no BUR",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(response.data) == 1, response.answer
    assert response.data[0]["nm_fantasa"] == "B"
    assert response.data[0]["score"] == pytest.approx(200 / 3)
    assert response.metadata["business_analysis"]["score"]["population"] == 2


def test_named_store_filter_precedes_customer_score():
    frame = receipts()
    frame.loc[frame.sk_loja.eq("A"), "nm_fantasa"] = "Renner"
    response = ask("Qual cliente foi mais engajado na loja Renner no BUR?", frame)
    assert len(response.data) == 1, response.answer
    assert response.metadata["business_analysis"]["score"]["population"] == 1
    assert response.data[0]["quantidade_compras"] == 4
    assert response.data[0]["score"] is None


def test_store_key_prevents_name_variants_from_changing_population():
    frame = receipts()
    variants = frame.sk_loja.eq("A") & frame.index.to_series().mod(2).eq(1)
    frame.loc[variants, "nm_fantasa"] = "Alias A"
    response = ask("Quais lojas foram mais representativas no BUR?", frame)
    assert len(response.data) == 3
    assert response.metadata["business_analysis"]["score"]["population"] == 3
    assert response.data[0]["score"] == pytest.approx(200 / 3)


def test_ranking_target_is_not_confused_with_leading_geographic_filter():
    frame = receipts()
    frame["bairro"] = "Centro"
    response = ask("No bairro Centro, qual loja foi mais representativa no BUR?", frame)
    assert response.metadata["business_analysis"]["ranking_entity"] == "loja"
    assert len(response.data) == 3, response.answer
    assert "nm_fantasa" in response.data[0]


def test_missing_fields_are_explained_without_crashing_narrator():
    response = ask(
        "Qual loja foi mais representativa no BUR?", receipts().drop(columns="sk_cliente"),
    )
    assert "sk_cliente" in response.answer
    assert "necessários indisponíveis" in response.answer


def test_explicit_number_of_customers_takes_precedence_over_score():
    frame = receipts()
    frame["sk_cliente"] = [f"person-{i}" for i in range(len(frame))]
    response = ask("Qual loja foi mais representativa por número de clientes no BUR?", frame)
    assert response.data[0]["nm_fantasa"] == "A"
    assert all("score" not in row for row in response.data)
