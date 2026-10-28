from types import SimpleNamespace

import pandas as pd

from app.executor.operations.business_demographics import derive_age_groups


def derive(clients, births=None, labels=None):
    data = pd.DataFrame({"sk_cliente": clients, "vl_compra": [10] * len(clients)})
    if births is not None:
        data["dt_nascimento"] = births
    if labels is not None:
        data["faixa_etaria"] = labels
    before = data.copy(deep=True)
    context = SimpleNamespace(metadata={})
    result = derive_age_groups(data, context)
    assert result.vl_compra.sum() == data.vl_compra.sum()
    pd.testing.assert_frame_equal(data, before)
    return result, context


def test_absurd_future_invalid_and_null_birthdates_are_unknown():
    future = str(pd.Timestamp.now(tz="America/Sao_Paulo").year + 1) + "-01-01"
    result, context = derive(["a", "b", "c", "d"], ["1800-01-01", future, "invalid", None])
    assert result.faixa_etaria.tolist() == ["Não informado"] * 4
    assert context.metadata["business_analysis"]["notes"]


def test_conflicting_valid_birthdates_make_all_client_purchases_unknown():
    result, _ = derive(
        ["a", "a", "a", "b", "b"], ["2000-01-01", "2001-01-01", None, "2000-01-01", "2000-01-01"]
    )
    assert result.faixa_etaria.iloc[:3].tolist() == ["Não informado"] * 3
    assert result.faixa_etaria.iloc[3:].nunique() == 1
    assert result.faixa_etaria.iloc[3] != "Não informado"


def test_anonymous_receipts_are_not_treated_as_one_conflicting_client():
    result, _ = derive([None, None], ["2000-01-01", "1970-01-01"])
    assert result.faixa_etaria.nunique() == 2
    assert not result.faixa_etaria.eq("Não informado").any()


def test_declared_age_groups_validated_and_conflicting_client_labels_unknown():
    result, _ = derive(
        ["a", "a", "b", "c", None], labels=["18-24", "25-34", "60+", "invalid", "0-17"]
    )
    assert result.faixa_etaria.tolist() == [
        "Não informado",
        "Não informado",
        "60+",
        "Não informado",
        "0-17",
    ]


def test_missing_birthdate_and_labels_produces_unknown_without_dropping_rows():
    result, _ = derive(["a", None])
    assert result.faixa_etaria.tolist() == ["Não informado", "Não informado"]


def test_equivalent_date_formats_are_consistent_and_birth_overrides_declared_labels():
    result, _ = derive(["a", "a"], [20000101, "01/01/2000"], ["60+", "0-17"])
    assert result.faixa_etaria.nunique() == 1
    assert result.faixa_etaria.iloc[0] not in {"Não informado", "60+", "0-17"}
