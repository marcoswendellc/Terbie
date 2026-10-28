from types import SimpleNamespace

import pandas as pd
import pytest


def run(mode, rows=None, **options):
    from app.executor.operations.business_customers import analyze

    data = pd.DataFrame(
        rows
        or [
            ["a", 100, "X", "Centro", "18-24", "Moda"],
            ["a", 50, "X", "Centro", "18-24", "Alimentacao"],
            ["b", 50, "Y", "Sul", "25-34", "Moda"],
            ["c", 100, None, None, "25-34", "Moda"],
        ],
        columns=["sk_cliente", "vl_compra", "cidade", "bairro", "faixa_etaria", "segmento"],
    )
    data["__purchase"] = [(i,) for i in range(len(data))]
    data["nm_empreendimento"] = "Shopping"
    data["cd_promocao"] = 1
    context = SimpleNamespace(metadata={})
    result = analyze(data, mode, context, options)
    assert "sk_cliente" not in result
    return result, context


def test_frequency_counts_purchases_per_identified_client():
    result, _ = run("frequency")
    assert result.iloc[0]["frequencia_media"] == pytest.approx(4 / 3)


def test_concentration_uses_ceiling_and_reports_revenue_share():
    result, context = run("concentration")
    assert result.iloc[0]["clientes_top_10_pct"] == 1
    assert result.iloc[0]["participacao_receita_top_10_pct"] == 50
    assert context.metadata["business_analysis"]["notes"]


def test_age_metrics_counts_unique_clients_within_age():
    result, _ = run("age_metrics")
    young = result.set_index("faixa_etaria").loc["18-24"]
    assert young["frequencia_media"] == 2
    assert young["ticket_medio_por_compra"] == 75


def test_repeat_distinguishes_single_and_multiple_purchase_clients():
    result, _ = run("purchase_repeat")
    counts = result.set_index("perfil_compra")["clientes"].to_dict()
    assert counts == {"compra_unica": 2, "multiplas_compras": 1}


@pytest.mark.parametrize(
    "mode,columns",
    [
        ("age_segments", ["faixa_etaria", "segmento"]),
        ("geo_ranking", ["cidade", "bairro"]),
        ("geo_ticket", ["cidade"]),
        ("neighborhood_frequency", ["bairro"]),
    ],
)
def test_group_modes_keep_dimensions_and_metrics(mode, columns):
    result, _ = run(mode)
    assert set(columns + ["clientes_unicos", "quantidade_compras", "faturamento"]).issubset(
        result.columns
    )
    assert result["faturamento"].sum() == (600 if mode == "geo_ranking" else 300)


def test_outside_city_requires_an_explicit_shopping_city():
    result, _ = run("outside_city")
    assert result.iloc[0]["status"] == "missing_shopping_city"


def test_outside_city_excludes_unknowns_from_known_denominator():
    result, _ = run("outside_city", shopping_cities={"Shopping": "x"})
    row = result.iloc[0]
    assert row["clientes_cidade_conhecida"] == 2
    assert row["clientes_cidade_desconhecida"] == 1
    assert row["clientes_fora_cidade"] == 1
    assert row["proporcao_fora_cidade_conhecida"] == 0.5
    assert row["proporcao_cidade_desconhecida"] == pytest.approx(1 / 3)


def test_frequency_excludes_receipts_without_client_and_reports_count():
    result, context = run(
        "frequency",
        rows=[
            ["a", 10, "X", "Centro", "18-24", "Moda"],
            [None, 10, "X", "Centro", "18-24", "Moda"],
        ],
    )
    assert result.iloc[0]["frequencia_media"] == 1
    assert context.metadata["business_analysis"]["notes"]


def test_outside_city_all_unknown_returns_no_known_city_fraction():
    result, _ = run(
        "outside_city",
        rows=[
            ["a", 10, None, None, "18-24", "Moda"],
        ],
        cidade_shopping="X",
    )
    assert pd.isna(result.iloc[0]["proporcao_fora_cidade_conhecida"])
    assert result.iloc[0]["proporcao_cidade_desconhecida"] == 1


def test_age_segments_supports_canonical_segment_column():
    from app.executor.operations.business_customers import analyze

    frame = pd.DataFrame(
        {
            "sk_cliente": ["a"],
            "vl_compra": [10],
            "__purchase": [(1,)],
            "faixa_etaria": ["18-24"],
            "nm_segmento": ["Moda"],
        }
    )
    result = analyze(frame, "age_segments", SimpleNamespace(metadata={}), {})
    assert result.iloc[0]["nm_segmento"] == "Moda"


def test_concentration_global_scope_and_nonpositive_denominator():
    from app.executor.operations.business_customers import analyze

    frame = pd.DataFrame(
        {
            "sk_cliente": ["a", "b"],
            "vl_compra": [-10, 0],
            "__purchase": [(1,), (2,)],
            "cd_promocao": ["p1", "p2"],
        }
    )
    result = analyze(frame, "concentration", SimpleNamespace(metadata={}), {})
    assert len(result) == 1
    assert pd.isna(result.iloc[0]["participacao_receita_top_10_pct"])


def test_geography_returns_city_and_neighborhood_levels():
    result, _ = run("geo_ranking")
    assert set(result.nivel_geografico) == {"cidade", "bairro"}
    assert result.groupby("nivel_geografico").faturamento.sum().to_dict() == {
        "bairro": 300,
        "cidade": 300,
    }


def test_state_alone_cannot_answer_city_ranking():
    from app.executor.operations.business_customers import analyze

    frame = pd.DataFrame(
        {"sk_cliente": ["a"], "vl_compra": [1], "__purchase": [(1,)], "uf": ["GO"]}
    )
    result = analyze(frame, "geo_ranking", SimpleNamespace(metadata={}), {})
    assert result.iloc[0]["status"] == "missing_dimension"


def test_geo_ticket_aggregates_region_and_sorts_highest_first():
    from app.executor.operations.business_customers import analyze

    frame = pd.DataFrame(
        {
            "sk_cliente": ["a", "b", "c"],
            "vl_compra": [10, 30, 100],
            "__purchase": [(1,), (2,), (3,)],
            "regiao": ["Sul", "Sul", "Norte"],
            "cidade": ["A", "B", "C"],
        }
    )
    result = analyze(frame, "geo_ticket", SimpleNamespace(metadata={}), {})
    assert list(result.regiao) == ["Norte", "Sul"]
    assert list(result.ticket_medio_por_compra) == [100, 20]


def test_outside_city_ambiguous_residence_excluded_from_denominator():
    result, _ = run(
        "outside_city",
        rows=[
            ["a", 10, "X", "Centro", "18-24", "Moda"],
            ["a", 10, "Y", "Centro", "18-24", "Moda"],
            ["b", 10, "Y", "Sul", "18-24", "Moda"],
        ],
        cidade_shopping="X",
    )
    row = result.iloc[0]
    assert row["clientes_cidade_conhecida"] == 1
    assert row["clientes_cidade_conflitante"] == 1
    assert row["proporcao_fora_cidade_conhecida"] == 1
