"""Business questions checked against independently calculated answers."""

import random

import pandas as pd
import pytest
from test_recent_campaign import service

from app.knowledge.knowledge_service import KnowledgeService

CAMPAIGN = "Promoção Mães E Namorados 2026"
METRICS = (
    "faturamento, quantidade de compras, clientes únicos, "
    "ticket médio por compra e ticket médio por cliente"
)
DIMENSIONS = [
    ("segmento", "nm_segmento"),
    ("segmento (nm_segmento)", "nm_segmento"),
    ("gênero", "genero"),
    ("gênero (genero)", "genero"),
    ("loja", "nm_fantasa"),
    ("bairro", "bairro"),
    ("cidade", "cidade"),
]


def business_frame():
    rows = []
    for index in range(24):
        rows.append(
            {
                "nm_promocao": CAMPAIGN,
                "cd_promocao": "p1",
                "nm_empreendimento": "Buriti Shopping",
                "sk_dtinicio": 20260501,
                "sk_dtfim": 20260612,
                "vl_compra": (index + 1) * 10.0,
                "cd_compra": f"purchase-{index}",
                "sk_cliente": f"client-{index // 2}",
                "nm_segmento": "Moda" if index % 2 else "Alimentação",
                "nm_fantasa": "Loja A" if index % 2 else "Loja B",
                "bairro": "Centro" if index % 2 else "Sul",
                "cidade": "Goiânia" if index % 2 else "Aparecida",
                "cd_sexo": "F" if index % 2 else "M",
            }
        )
    for updates in [
        {"nm_promocao": "Outra campanha"},
        {"nm_empreendimento": "Shopping Sul"},
        {"sk_dtinicio": 20250501, "sk_dtfim": 20250612},
    ]:
        rows.append(
            {
                **rows[0],
                **updates,
                "vl_compra": 999999.0,
                "cd_compra": str(updates),
                "sk_cliente": str(updates),
            }
        )
    return pd.DataFrame(rows)


CASES = [
    (label, field, phrase)
    for label, field in DIMENSIONS
    for phrase in [f"Qual foi o {METRICS}", "Mostre o faturamento"]
]
random.Random(20260928).shuffle(CASES)


@pytest.mark.parametrize("label,field,phrase", CASES)
def test_varied_questions_match_independent_grouped_totals(label, field, phrase):
    frame = business_frame()
    response = service(frame=frame).execute_question(
        question=f'{phrase} da "{CAMPAIGN}" do Buriti Shopping por {label} em 2026?',
        knowledge_context=KnowledgeService().get_context(),
    )
    expected = frame.iloc[:24].copy()
    expected["genero"] = expected.cd_sexo.map({"F": "Feminino", "M": "Masculino"})
    assert len(response.data) == expected[field].nunique(), response.answer
    for row in response.data:
        assert field in row, response.answer
        group = expected[expected[field] == row[field]]
        assert row["faturamento"] == pytest.approx(group.vl_compra.sum())
        assert str(row[field]) in response.answer
        if "clientes únicos" in phrase:
            assert row["quantidade_compras"] == group.cd_compra.nunique()
            assert row["clientes_unicos"] == group.sk_cliente.nunique()
            assert row["ticket_medio_por_compra"] == pytest.approx(
                group.vl_compra.sum() / group.cd_compra.nunique()
            )
            assert row["ticket_medio_por_cliente"] == pytest.approx(
                group.vl_compra.sum() / group.sk_cliente.nunique()
            )


def test_missing_grouping_column_never_returns_overall_total():
    response = service(frame=business_frame().drop(columns="nm_segmento")).execute_question(
        question=f'Qual o {METRICS} da "{CAMPAIGN}" por segmento?',
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data == []
    assert response.metadata["response_type"] == "analysis_failed"


def test_director_cannot_drop_explicit_gender_breakdown():
    from test_conversational_analysis import DirectorProvider

    from app.conversation.models import AnalysisDecision, AnalysisQuestion

    provider = DirectorProvider(
        AnalysisDecision(
            analyses=[
                AnalysisQuestion(title="Total", question=f'Qual o faturamento da "{CAMPAIGN}"?')
            ]
        )
    )
    response = service(provider, business_frame()).execute_question(
        question=f'Qual o {METRICS} da "{CAMPAIGN}" do Buriti Shopping por gênero em 2026?',
        knowledge_context=KnowledgeService().get_context(),
    )
    assert {row.get("genero") for row in response.data} == {"Feminino", "Masculino"}


@pytest.mark.parametrize("field,label", [("nm_segmento", "segmento"), ("bairro", "bairro")])
def test_numeric_group_labels_remain_dimensions_in_visible_answer(field, label):
    frame = business_frame()
    frame[field] = [53 if index % 2 else "Centro" for index in range(len(frame))]
    response = service(frame=frame).execute_question(
        question=f'Mostre faturamento da "{CAMPAIGN}" do Buriti Shopping por {label} em 2026',
        knowledge_context=KnowledgeService().get_context(),
    )
    assert len(response.data) == 2
    assert "Centro" in response.answer
    assert "53" in response.answer
    assert "1.560,00" in response.answer and "1.440,00" in response.answer


@pytest.mark.parametrize("with_director", [False, True])
@pytest.mark.parametrize(
    "follow_up", ["E o faturamento por gênero nessa campanha?", "E por gênero?"]
)
def test_follow_up_breakdown_preserves_campaign_shopping_and_year(with_director, follow_up):
    from test_conversational_analysis import DirectorProvider

    instance = service(DirectorProvider(None) if with_director else None, business_frame())
    knowledge = KnowledgeService().get_context()
    instance.execute_question(
        question=f'Faturamento da "{CAMPAIGN}" do Buriti Shopping por segmento em 2026',
        knowledge_context=knowledge,
        session_id="scope",
    )
    response = instance.execute_question(
        question=follow_up,
        knowledge_context=knowledge,
        session_id="scope",
    )
    assert {row["genero"]: row["faturamento"] for row in response.data} == {
        "Feminino": 1560,
        "Masculino": 1440,
    }
