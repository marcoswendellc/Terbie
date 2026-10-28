import pandas as pd
import pytest
from test_conversational_analysis import DirectorProvider
from test_recent_campaign import service

from app.conversation.models import AnalysisDecision, AnalysisQuestion
from app.knowledge.knowledge_service import KnowledgeService

QUESTION = "Existem diferenças significativas no comportamento de compra entre homens e mulheres?"


def purchases(n=24, same=False):
    rows = []
    for sex in ["F", "M"]:
        for i in range(n):
            for j in range(1 + i % 3):
                rows.append({
                    "cd_sexo": sex, "sk_cliente": f"{sex}{i}",
                    "cd_compra": f"{sex}{i}-{j}",
                    "vl_compra": 10 + i + (0 if same or sex == "F" else 100),
                    "nm_promocao": "Promoção Mães E Namorados 2026",
                    "cd_promocao": "13718", "nm_empreendimento": "Buriti Shopping",
                    "dt_registro_mos": "2026-05-15", "sk_dtinicio": 20260501,
                    "sk_dtfim": 20260612,
                })
    return pd.DataFrame(rows)


def ask(frame, question=QUESTION, provider=None):
    return service(provider, frame).execute_question(
        question=question, knowledge_context=KnowledgeService().get_context(),
        session_id="gender-test",
    )


def test_gender_comparison_uses_clients_and_matches_welch_reference():
    from scipy.stats import ttest_ind

    frame = purchases()
    result = ask(pd.concat([frame, frame.iloc[[0]]], ignore_index=True))
    assert [row["genero"] for row in result.data] == ["Feminino", "Masculino"]
    assert [row["clientes_unicos"] for row in result.data] == [24, 24]
    assert sum(row["quantidade_compras"] for row in result.data) == len(frame)
    clients = frame.groupby(["cd_sexo", "sk_cliente"]).vl_compra.mean()
    reference = ttest_ind(clients.loc["M"], clients.loc["F"], equal_var=False)
    tests = result.metadata["gender_comparison"]["tests"]
    ticket = next(item for item in tests if item["metric"] == "ticket_por_cliente")
    assert ticket["p_value"] == pytest.approx(reference.pvalue)
    assert ticket["ci_low"] == pytest.approx(reference.confidence_interval().low)
    assert ticket["difference"] == pytest.approx(100)
    assert ticket["significant"] is True
    assert ticket["adjusted_p_value"] >= ticket["p_value"]
    assert "Holm" in result.answer
    assert "causalidade" in result.answer
    assert "visitantes" in result.answer
    assert "\n\n|---" not in result.answer
    assert "\n| Feminino |" in result.answer


def test_equal_distributions_do_not_claim_equivalence():
    result = ask(purchases(same=True))
    assert all(not item["significant"] for item in result.metadata["gender_comparison"]["tests"])
    assert "não comprova igualdade" in result.answer


@pytest.mark.parametrize("n", [1, 5, 19])
def test_small_groups_are_descriptive_only(n):
    result = ask(purchases(n))
    assert len(result.data) == 2
    assert all(item["p_value"] is None for item in result.metadata["gender_comparison"]["tests"])
    assert "20 clientes" in result.answer


def test_conflicting_and_unknown_gender_clients_are_excluded():
    frame = purchases()
    conflict = frame.iloc[[0]].copy()
    conflict["cd_sexo"] = "M"
    conflict["cd_compra"] = "conflicting-client"
    unknown = frame.iloc[[0]].copy()
    unknown["sk_cliente"] = "unknown"
    unknown["cd_compra"] = "unknown"
    unknown["cd_sexo"] = "O"
    result = ask(pd.concat([frame, conflict, unknown], ignore_index=True))
    assert [row["clientes_unicos"] for row in result.data] == [23, 24]
    assert result.metadata["gender_comparison"]["excluded_clients"] == 2


def test_explicit_scope_resists_director_rewrite_and_other_campaigns():
    frame = purchases()
    outside = frame.copy()
    outside["nm_promocao"] = "No Pelo 360 com Hugo e Guilherme e Buriti Shopping"
    outside["vl_compra"] = 999999
    provider = DirectorProvider(AnalysisDecision(analyses=[AnalysisQuestion(
        title="Wrong", question="Qual o faturamento da campanha No Pelo 360?",
    )]))
    result = ask(pd.concat([frame, outside], ignore_index=True),
                 QUESTION + " Na promoção mães 2026 do Buriti Shopping.", provider)
    assert sum(row["faturamento"] for row in result.data) == frame.vl_compra.sum()
    assert "Mães E Namorados 2026" in result.answer


def test_one_missing_gender_has_no_inference():
    result = ask(purchases().query("cd_sexo == 'F'"))
    assert len(result.data) == 1
    assert all(item["p_value"] is None for item in result.metadata["gender_comparison"]["tests"])


def test_numeric_gender_codes_with_missing_spreadsheet_cell():
    frame = purchases()
    frame["cd_sexo"] = frame.cd_sexo.map({"F": 0.0, "M": 1.0})
    missing = frame.iloc[[0]].copy()
    missing["cd_sexo"] = float("nan")
    missing["sk_cliente"] = "unknown"
    missing["cd_compra"] = "unknown"
    result = ask(pd.concat([frame, missing], ignore_index=True))
    assert [row["clientes_unicos"] for row in result.data] == [24, 24]
    assert result.metadata["gender_comparison"]["excluded_clients"] == 1


@pytest.mark.parametrize("suffix", ["em maio/26", "em 2026"])
def test_explicit_purchase_period_excludes_other_periods(suffix):
    frame = purchases()
    outside = frame.copy()
    outside["dt_registro_mos"] = "2025-05-15"
    outside["cd_compra"] += "-outside"
    outside["vl_compra"] = 999999
    result = ask(pd.concat([frame, outside], ignore_index=True), QUESTION + " " + suffix)
    assert sum(row["faturamento"] for row in result.data) == frame.vl_compra.sum()
    assert "Compras de" in result.answer


@pytest.mark.parametrize("invalid", [None, "inválido", float("inf")])
def test_invalid_purchase_amount_excludes_the_whole_client(invalid):
    frame = purchases()
    frame["vl_compra"] = frame.vl_compra.astype(object)
    frame.loc[0, "vl_compra"] = invalid
    result = ask(frame)
    assert [row["clientes_unicos"] for row in result.data] == [23, 24]
    assert result.metadata["gender_comparison"]["excluded_clients"] == 1


def test_conflicting_receipt_does_not_arbitrarily_keep_first_amount():
    frame = purchases()
    conflict = frame.iloc[[0]].copy()
    conflict["vl_compra"] = 9999
    result = ask(pd.concat([frame, conflict], ignore_index=True))
    assert [row["clientes_unicos"] for row in result.data] == [23, 24]


def test_holm_adjustment_is_bounded_and_never_less_than_raw_p():
    # Build all three nondegenerate outcomes with only a modest difference.
    frame = purchases(same=True)
    extra = frame[(frame.cd_sexo == "M") & (frame.cd_compra.str.endswith("-0"))].copy()
    extra["cd_compra"] += "-extra"
    extra["vl_compra"] += 3
    result = ask(pd.concat([frame, extra], ignore_index=True))
    tests = result.metadata["gender_comparison"]["tests"]
    assert all(0 <= item["p_value"] <= item["adjusted_p_value"] <= 1 for item in tests)
    ordered = sorted(tests, key=lambda item: item["p_value"])
    adjusted = [item["adjusted_p_value"] for item in ordered]
    assert adjusted == sorted(adjusted)
