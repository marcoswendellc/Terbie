import pandas as pd
import pytest

from app.executor.operations.business_score import add_percentile_score


def indicators():
    return pd.DataFrame({
        "loja": ["A", "B", "C"],
        "faturamento": [100, 120, 200],
        "quantidade_compras": [4, 2, 1],
        "ticket_medio_por_compra": [25, 60, 200],
    })


def test_score_is_mean_of_three_percentiles_on_full_population():
    result = add_percentile_score(indicators())
    assert result.percentil_faturamento.tolist() == [0, 50, 100]
    assert result.percentil_compras.tolist() == [100, 50, 0]
    assert result.percentil_ticket.tolist() == [0, 50, 100]
    assert result.score.tolist() == pytest.approx([100 / 3, 50, 200 / 3])


def test_equal_values_have_equal_midpoint_percentiles():
    data = indicators()
    data.iloc[:, 1:] = [10, 1, 10]
    result = add_percentile_score(data)
    assert result.score.tolist() == pytest.approx([50, 50, 50])


def test_single_entity_has_no_comparative_score():
    result = add_percentile_score(indicators().iloc[:1])
    assert result.score.isna().all()


def test_missing_or_nonfinite_indicators_do_not_enter_percentile_population():
    data = indicators()
    invalid = pd.DataFrame({
        "loja": ["missing", "infinite", "zero"],
        "faturamento": [None, float("inf"), 0],
        "quantidade_compras": [1, 1, 0],
        "ticket_medio_por_compra": [10, 10, 0],
    })
    result = add_percentile_score(pd.concat([data, invalid], ignore_index=True))
    assert result.loja.tolist() == ["A", "B", "C"]
    assert result.score.tolist() == pytest.approx([100 / 3, 50, 200 / 3])


def test_weights_are_configurable_without_changing_percentiles():
    result = add_percentile_score(indicators(), {
        "faturamento": 0, "quantidade_compras": 1, "ticket_medio_por_compra": 0,
    })
    assert result.score.tolist() == [100, 50, 0]


@pytest.mark.parametrize("weights", [
    {}, {"faturamento": 1},
    {"faturamento": -1, "quantidade_compras": 1, "ticket_medio_por_compra": 1},
    {"faturamento": 0, "quantidade_compras": 0, "ticket_medio_por_compra": 0},
    {"faturamento": float("nan"), "quantidade_compras": 1, "ticket_medio_por_compra": 1},
])
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):
        add_percentile_score(indicators(), weights)
