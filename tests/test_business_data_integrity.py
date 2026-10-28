from types import SimpleNamespace

import pandas as pd

from app.executor.operations.business_common import campaign_keys, prepare, summarize
from app.semantic.business_analysis import explicit_business_scope


def context():
    return SimpleNamespace(metadata={})


def test_missing_shopping_ids_do_not_merge_different_shops_receipt_numbers():
    frame = pd.DataFrame(
        {
            "cd_compra": ["1", "1"],
            "cd_empreendimento": [None, None],
            "nm_empreendimento": ["Shopping A", "Shopping B"],
            "vl_compra": [10, 20],
            "sk_cliente": ["a", "b"],
        }
    )
    cleaned = prepare(frame, context())
    assert len(cleaned) == 2
    assert cleaned.__purchase.nunique() == 2


def test_stable_campaign_id_does_not_split_changed_display_names():
    frame = pd.DataFrame(
        {
            "cd_compra": ["1", "2"],
            "cd_empreendimento": [1, 1],
            "nm_empreendimento": ["Buriti Shopping", "BURITI SHOPPING"],
            "cd_promocao": ["p1", "p1"],
            "nm_promocao": ["Natal", "NATAL"],
            "vl_compra": [10, 20],
            "sk_cliente": ["a", "a"],
        }
    )
    cleaned = prepare(frame, context())
    assert len(summarize(cleaned, campaign_keys(cleaned))) == 1


def test_conflicting_receipt_dates_are_not_chosen_by_input_order():
    frame = pd.DataFrame(
        {
            "cd_compra": ["1", "1"],
            "vl_compra": [10, 10],
            "sk_cliente": ["a", "a"],
            "dt_registro_mos": ["2026-01-01", "2026-01-04"],
        }
    )
    assert prepare(frame, context()).empty
    assert prepare(frame.iloc[::-1], context()).empty


def test_campaign_name_prepositions_are_not_scope_separators():
    scope = explicit_business_scope(
        "Qual frequência média de compras por cliente na campanha Dia da Mulher 2026 "
        "do Buriti Shopping?"
    )
    assert scope["campaign"] == "dia da mulher 2026"
    assert scope["shopping"] == "buriti shopping"


def test_partially_missing_ids_use_unambiguous_existing_identity():
    frame = pd.DataFrame(
        {
            "cd_compra": ["1", "1"],
            "cd_empreendimento": [1, None],
            "nm_empreendimento": ["Shopping A", "Shopping A"],
            "cd_promocao": ["p1", None],
            "nm_promocao": ["Natal", "Natal"],
            "vl_compra": [10, 10],
            "sk_cliente": ["a", "a"],
        }
    )
    cleaned = prepare(frame, context())
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["cd_promocao"] == "p1"
