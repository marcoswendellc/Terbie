from types import SimpleNamespace

import pandas as pd
import pytest

from app.executor.operations.business_segments import analyze


def context():
    return SimpleNamespace(metadata={})


def receipts():
    return pd.DataFrame(
        [
            (1, "c1", "A", 100, "S1", "l1", "Loja", "p1", "Natal"),
            (2, "c1", "B", 50, "S1", "l2", "Outra", "p1", "Natal"),
            (3, "c2", "A", 50, "S2", "l1", "Loja", "p1", "Natal"),
            (4, None, "B", 0, "S1", "l2", "Outra", "p1", "Natal"),
        ],
        columns=[
            "__purchase",
            "sk_cliente",
            "nm_segmento",
            "vl_compra",
            "nm_empreendimento",
            "sk_loja",
            "nm_fantasa",
            "cd_promocao",
            "nm_promocao",
        ],
    )


def test_segment_share_uses_revenue_and_purchase_denominators():
    result = analyze(receipts(), "segment_share", context(), {}).set_index("nm_segmento")
    assert result.loc["A", "participacao_faturamento_pct"] == 75
    assert result.loc["B", "participacao_compras_pct"] == 50


@pytest.mark.parametrize("amounts", [[0, 0, 0, 0], [-100, 0, 0, 0]])
def test_nonpositive_revenue_denominator_is_undefined(amounts):
    data = receipts()
    data["vl_compra"] = amounts
    result = analyze(data, "segment_share", context(), {})
    assert result.participacao_faturamento_pct.isna().all()


def test_store_customer_ranking_preserves_shopping_identity():
    result = analyze(receipts(), "store_customers", context(), {})
    assert len(result) == 3
    assert result.clientes_unicos.tolist() == [1, 1, 1]
    assert "sk_cliente" not in result


def test_segment_recurrence_and_campaign_frequency_are_client_weighted():
    data = receipts()
    data.loc[1, "nm_segmento"] = "A"
    result = analyze(data, "segment_recurrence", context(), {}).set_index("nm_segmento")
    assert result.loc["A", "frequencia_media"] == 1.5
    assert result.loc["A", "ticket_medio_por_compra"] == pytest.approx(200 / 3)
    campaigns = analyze(data, "campaign_frequency", context(), {}).set_index("nm_empreendimento")
    assert campaigns.loc["S1", "frequencia_media"] == 2
    assert campaigns.loc["S1", "ticket_medio_por_cliente"] == 150
    assert "sk_cliente" not in campaigns


def test_campaign_ranking_separates_same_name_between_shoppings():
    result = analyze(receipts(), "campaign_ranking", context(), {})
    assert len(result) == 2
    assert result.faturamento.tolist() == [150, 50]


def test_segment_pairs_count_membership_once_and_exclude_missing_clients():
    data = receipts()
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    analysis_context = context()
    result = analyze(data, "segment_pairs", analysis_context, {})
    assert len(result) == 1
    assert result.iloc[0][["segmento_a", "segmento_b"]].tolist() == ["A", "B"]
    assert result.iloc[0].clientes_em_comum == 1
    assert result.iloc[0].suporte_pct == 50


def test_segment_pairs_refuses_excess_work_without_partial_results():
    result = analyze(receipts(), "segment_pairs", context(), {"max_pair_expansions": 0})
    assert result.iloc[0].status == "recusado"
    assert "pares" in result.iloc[0].motivo


def test_empty_pairs_has_stable_schema():
    result = analyze(receipts().iloc[:0], "segment_pairs", context(), {})
    assert result.columns.tolist() == [
        "segmento_a",
        "segmento_b",
        "clientes_em_comum",
        "suporte_pct",
    ]


def test_pair_support_can_overlap_across_multiple_memberships():
    data = receipts().iloc[[0, 1]].copy()
    third = data.iloc[[0]].copy()
    third["__purchase"] = 5
    third["nm_segmento"] = "C"
    data = pd.concat([data, third], ignore_index=True)
    result = analyze(data, "segment_pairs", context(), {})
    assert len(result) == 3
    assert result.clientes_em_comum.tolist() == [1, 1, 1]
    assert result.suporte_pct.tolist() == [100, 100, 100]


def test_ranking_does_not_implicitly_limit_to_ten_results():
    data = pd.concat([receipts().iloc[[0]]] * 12, ignore_index=True)
    data["nm_segmento"] = [f"Segmento {number:02d}" for number in range(12)]
    data["__purchase"] = range(12)
    result = analyze(data, "segment_share", context(), {})
    assert len(result) == 12
    assert len(analyze(data, "segment_share", context(), {"limit": 3})) == 3


def test_segment_recurrence_ranks_purchase_ticket_above_total_revenue():
    data = receipts()
    data["nm_segmento"] = ["A", "A", "A", "B"]
    data["vl_compra"] = [40, 40, 40, 100]
    result = analyze(data, "segment_recurrence", context(), {})
    assert result.nm_segmento.tolist() == ["B", "A"]
    assert result.ticket_medio_por_compra.tolist() == [100, 40]
    assert result.faturamento.tolist() == [100, 120]
    assert "frequencia_media" in result


def test_campaign_frequency_ranks_frequency_above_revenue():
    data = receipts().iloc[:3].copy()
    data["vl_compra"] = [10, 10, 1000]
    result = analyze(data, "campaign_frequency", context(), {})
    assert result.nm_empreendimento.tolist() == ["S1", "S2"]
    assert result.frequencia_media.tolist() == [2, 1]
    assert result.ticket_medio_por_cliente.tolist() == [20, 1000]


def test_pair_denominator_excludes_clients_without_any_known_segment():
    data = receipts()
    unknown = data.iloc[[0]].copy()
    unknown["sk_cliente"] = "c3"
    unknown["nm_segmento"] = None
    unknown["__purchase"] = 5
    data = pd.concat([data, unknown], ignore_index=True)
    result = analyze(data, "segment_pairs", context(), {})
    assert result.iloc[0].clientes_em_comum == 1
    assert result.iloc[0].suporte_pct == 50


def test_pairs_return_all_combinations_without_an_implicit_result_limit():
    data = pd.concat([receipts().iloc[[0]]] * 6, ignore_index=True)
    data["nm_segmento"] = list("ABCDEF")
    data["__purchase"] = range(6)
    result = analyze(data, "segment_pairs", context(), {})
    assert len(result) == 15
    assert result.clientes_em_comum.eq(1).all()
    assert result.suporte_pct.eq(100).all()
