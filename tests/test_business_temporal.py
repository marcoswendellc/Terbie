from types import SimpleNamespace

import pandas as pd

from app.executor.operations.business_temporal import analyze


def frame():
    return pd.DataFrame(
        [
            dict(
                nm_empreendimento="Sul",
                cd_promocao=campaign,
                nm_promocao=campaign,
                sk_cliente=client,
                vl_compra=value,
                __purchase=(campaign, index),
                dt_registro_mos=date,
                sk_dtinicio=start,
                sk_dtfim=end,
            )
            for index, (campaign, client, value, date, start, end) in enumerate(
                [
                    ("A", "c1", 100, "2026-01-01", 20260101, 20260109),
                    ("A", "c1", 200, "2026-01-04", 20260101, 20260109),
                    ("A", "c2", 300, "2026-01-04", 20260101, 20260109),
                    ("B", "c1", 400, "2026-02-01", 20260201, 20260209),
                    ("B", "c3", 600, "2026-02-02", 20260201, 20260209),
                ]
            )
        ]
    )


def run(mode, data=None):
    context = SimpleNamespace(metadata={}, warnings=[])
    return analyze(frame() if data is None else data, mode, context, {}), context


def test_weekdays_follow_calendar_order_and_total_revenue():
    result, _ = run("weekday")
    assert result.dia_semana_ordem.tolist() == [0, 3, 6]
    assert result.faturamento.sum() == 1600
    assert "sk_cliente" not in result


def test_ticket_evolution_keeps_campaign_and_calendar_day():
    result, _ = run("ticket_evolution")
    day = result[(result.nm_promocao == "A") & (result.data_compra == "2026-01-04")]
    assert day.iloc[0].ticket_medio_por_compra == 250
    assert len(result) == 4


def test_phases_use_declared_calendar_bounds_include_empty_phase_and_new_denominator():
    result, _ = run("campaign_phases")
    campaign = result[result.nm_promocao == "A"]
    assert campaign.fase.tolist() == ["Início", "Meio", "Fim"]
    assert campaign.clientes_unicos.tolist() == [1, 2, 0]
    assert campaign.clientes_novos.tolist() == [1, 1, 0]
    assert campaign.denominador_clientes_campanha.tolist() == [2, 2, 2]
    assert campaign.participacao_clientes.tolist() == [0.5, 1.0, 0.0]
    assert campaign.data_inicio_fase.tolist() == ["2026-01-01", "2026-01-04", "2026-01-07"]


def test_phases_never_invent_missing_campaign_bounds():
    data = frame().drop(columns=["sk_dtinicio", "sk_dtfim"])
    result, context = run("campaign_phases", data)
    assert result.status.eq("periodo_campanha_indisponivel").all()
    assert "fase" not in result
    assert context.metadata or context.warnings


def test_retention_membership_and_returning_cohort_use_stable_client_ids():
    result, _ = run("campaign_retention", frame().iloc[::-1])
    assert result.nm_promocao.tolist() == ["A", "B"]
    assert result.denominador_clientes.tolist() == [3, 3]
    assert result.clientes_multicampanha.tolist() == [1, 1]
    assert result.participacao_multicampanha.tolist() == [1 / 3, 1 / 3]
    assert result.clientes_retornantes.tolist() == [0, 1]
    assert result.iloc[1].gasto_medio_retornantes == 400
    assert result.iloc[1].gasto_medio_retornantes_anterior == 300
    assert result.iloc[1].variacao_gasto_retornantes == 100
    assert "sk_cliente" not in result


def test_retention_missing_start_does_not_invent_chronology():
    result, _ = run("campaign_retention", frame().drop(columns="sk_dtinicio"))
    assert result.status.eq("ordem_cronologica_indisponivel").all()
    assert result.clientes_multicampanha.tolist() == [1, 1]


def test_missing_purchase_dates_returns_informative_status():
    result, _ = run("weekday", frame().drop(columns="dt_registro_mos"))
    assert result.iloc[0].status == "datas_compras_indisponiveis"


def test_simultaneous_campaigns_both_compare_to_strictly_earlier_campaign():
    data = frame()
    other = data[data.nm_promocao.eq("B")].copy()
    other["nm_promocao"] = "C"
    other["cd_promocao"] = "C"
    other["__purchase"] = [("C", i) for i in range(len(other))]
    result, _ = run("campaign_retention", pd.concat([data, other], ignore_index=True))
    assert result.clientes_retornantes.tolist() == [0, 1, 1]
