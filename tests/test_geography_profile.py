import pandas as pd
import pytest
from test_recent_campaign import service

from app.knowledge.knowledge_service import KnowledgeService


def frame():
    rows = []
    for city, uf, value, count in [
        ("Goiânia", "GO", 100, 6),
        ("Aparecida de Goiânia", "GO", 200, 3),
        ("São Paulo", "SP", 500, 2),
    ]:
        for i in range(count):
            rows.append(
                {
                    "localidade": city,
                    "uf": uf,
                    "bairro": "Centro" if uf == "GO" else "Sul",
                    "vl_compra": value,
                    "cd_compra": f"{city}-{i}",
                    "sk_cliente": f"{city}-{i}",
                    "dt_registro_mos": "2026-05-10",
                    "cd_sexo": "F" if i % 2 == 0 else "M",
                    "dt_nascimento": "1990-01-01",
                }
            )
    rows.append(
        {
            **rows[0],
            "dt_registro_mos": "2026-06-10",
            "vl_compra": 900,
            "cd_compra": "june",
            "sk_cliente": "june",
        }
    )
    rows.append(
        {
            **rows[0],
            "dt_registro_mos": "2025-05-10",
            "vl_compra": 9000,
            "cd_compra": "last-year",
            "sk_cliente": "last-year",
        }
    )
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "place,expected",
    [
        ("goiânia", 1312.5),
        ("aparecida de goiânia", 200),
        ("GO", 11100 / 11),
        ("SP", 500),
        ("estado de SP", 500),
    ],
)
def test_ticket_filters_city_or_state_instead_of_repeating_global_value(place, expected):
    result = service(frame=frame()).execute_question(
        question=f"qual o ticket médio de {place}?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(result.data) == 1
    assert result.data[0]["ticket_medio_por_compra"] == pytest.approx(expected)


def test_unknown_city_does_not_return_global_ticket():
    result = service(frame=frame()).execute_question(
        question="Qual o ticket médio de Cidade Inexistente?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data == []


def test_neighborhood_ranking_excludes_other_years():
    dataset = frame()
    missing = pd.DataFrame(
        [{**dataset.iloc[0], "bairro": "NULL", "cd_compra": f"null-{i}"} for i in range(20)]
    )
    result = service(frame=pd.concat([dataset, missing], ignore_index=True)).execute_question(
        question="qual bairro apresentou maior volume de notas cadastradas em 2026?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data == [{"bairro": "Centro", "quantidade_compras": 10}]


def test_may_profile_has_correct_population_and_analytical_summary():
    result = service(frame=frame()).execute_question(
        question="qual o perfil dos clientes das compras em maio/26?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data[0]["clientes_unicos"] == 11
    assert result.data[0]["quantidade_compras"] == 11
    assert "%" in result.answer
    assert "maio" in result.answer.lower() or "2026-05" in result.answer
    assert "registrad" in result.answer.lower()


def test_state_follow_up_changes_geography_without_losing_metric():
    instance = service(frame=frame())
    k = KnowledgeService().get_context()
    instance.execute_question(
        question="Qual o ticket médio de Goiânia?", knowledge_context=k, session_id="geo"
    )
    result = instance.execute_question(question="e do GO?", knowledge_context=k, session_id="geo")
    assert result.data[0]["ticket_medio_por_compra"] == pytest.approx(11100 / 11)


@pytest.mark.parametrize(
    "metric,denominator", [("por compra", "cd_compra"), ("por cliente", "sk_cliente")]
)
def test_state_follow_up_preserves_may_and_ticket_denominator(metric, denominator):
    dataset = frame()
    dataset.loc[:5, "sk_cliente"] = "repeat-customer"
    instance = service(frame=dataset)
    k = KnowledgeService().get_context()
    instance.execute_question(
        question=f"Qual o ticket médio {metric} de Goiânia em maio/26?",
        knowledge_context=k,
        session_id="scoped-geo",
    )
    result = instance.execute_question(
        question="e do GO?", knowledge_context=k, session_id="scoped-geo"
    )
    expected = dataset[dataset.uf.eq("GO") & dataset.dt_registro_mos.eq("2026-05-10")]
    key = "ticket_medio_por_cliente" if denominator == "sk_cliente" else "ticket_medio_por_compra"
    assert result.data[0][key] == pytest.approx(
        expected.vl_compra.sum() / expected[denominator].nunique()
    )


def test_geography_filter_preserves_requested_neighborhood_breakdown():
    dataset = frame()
    dataset.loc[0, "bairro"] = "Norte"
    result = service(frame=dataset).execute_question(
        question="Qual o ticket médio de Goiânia por bairro?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert {row["bairro"] for row in result.data} == {"Norte", "Centro"}


def test_clients_by_state_are_actually_grouped():
    result = service(frame=frame()).execute_question(
        question="Mostre clientes únicos por UF em 2026",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert {row["uf"]: row["clientes_unicos"] for row in result.data} == {"GO": 10, "SP": 2}


def test_profile_birth_dates_preserve_iso_month_and_day():
    from app.executor.context import ExecutionContext
    from app.executor.operations.derive_demographics import DeriveDemographicsOperation
    from app.planner.models import PlanOperation

    data = pd.DataFrame({"dt_nascimento": ["2000-10-05"], "cd_sexo": ["F"]})
    result = DeriveDemographicsOperation().execute(
        data,
        PlanOperation(type="derive_demographics"),
        ExecutionContext(knowledge_context=KnowledgeService().get_context()),
    )
    today = pd.Timestamp.now()
    expected = today.year - 2000 - int((today.month, today.day) < (10, 5))
    assert result.iloc[0]["idade"] == expected


@pytest.mark.parametrize("with_director", [False, True])
def test_home_campaign_participant_profile_is_recognized_and_scoped(with_director):
    from test_conversational_analysis import DirectorProvider

    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    dataset = frame()
    dataset["cd_promocao"] = None
    dataset.loc[:5, "cd_promocao"] = "campaign"
    provider = (
        DirectorProvider(
            AnalysisDecision(
                analyses=[
                    AnalysisQuestion(
                        title="Incorrect rewrite", question="Qual o faturamento total?"
                    )
                ]
            )
        )
        if with_director
        else None
    )
    result = service(provider, dataset).execute_question(
        question="Qual é o perfil dos participantes das campanhas?",
        knowledge_context=KnowledgeService().get_context(),
    )
    assert result.data, result.answer
    assert result.data[0]["clientes_unicos"] == 6
    assert "genero_predominante" in result.data[0]
    assert "registrad" in result.answer.lower()
