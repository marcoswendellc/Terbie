"""Independent arithmetic recheck; source read only, no model invocation."""

import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from app.core.dependencies import provide_execution_service
from scripts.evaluate_director import parse_source_dates


def main():
    logging.disable(logging.CRITICAL)
    engine = provide_execution_service()
    frame = engine._load_dataframes()[engine._settings.default_table]
    amount = frame.vl_compra.astype(str).str.replace("R$", "", regex=False).str.strip()
    comma = amount.str.contains(",", regex=False)
    amount.loc[comma] = (
        amount.loc[comma].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    )
    frame = frame.assign(vl_compra=pd.to_numeric(amount, errors="raise"))
    dates = parse_source_dates(frame.dt_registro_mos)
    monthly = frame.loc[dates.dt.year.eq(2026)].assign(
        mes=dates[dates.dt.year.eq(2026)].dt.strftime("%Y-%m")
    )
    totals = monthly.groupby("mes").vl_compra.sum().to_dict()
    people = frame.dropna(subset=["sk_cliente"]).drop_duplicates("sk_cliente").copy()
    gender = (
        people.cd_sexo.astype(str)
        .str.strip()
        .str.upper()
        .map({"0": "Feminino", "1": "Masculino", "F": "Feminino", "M": "Masculino", "O": "Outros"})
    )
    birth = parse_source_dates(people.dt_nascimento)
    today = date.today()
    ages = (
        today.year
        - birth.dt.year
        - (
            (birth.dt.month > today.month)
            | ((birth.dt.month == today.month) & (birth.dt.day > today.day))
        ).astype(int)
    )
    bands = pd.cut(
        ages,
        [-1, 17, 24, 34, 44, 54, 64, 150],
        labels=["0-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
    )
    city = people.cidade.astype("string").str.strip()
    city = city.mask(city.str.casefold().isin(["", "null", "none", "nan", "não informado"]))

    def dominant(series):
        counts = series.dropna().value_counts()
        return {
            "value": str(counts.index[0]),
            "count": int(counts.iloc[0]),
            "valid": int(series.notna().sum()),
            "share": float(counts.iloc[0] / series.notna().sum()),
        }

    oracle = {
        "source_rows": len(frame),
        "source_total": float(frame.vl_compra.sum()),
        "parsed_purchase_dates": int(dates.notna().sum()),
        "monthly_2026": totals,
        "profile": {
            "customers": len(people),
            "purchases": int(frame.cd_compra.nunique()),
            "ticket": float(frame.vl_compra.sum() / frame.cd_compra.nunique()),
            "gender": dominant(gender),
            "age_band": dominant(bands),
            "city": dominant(city),
        },
    }
    path = Path("evals/director-evaluation-2026-09-30-oracle.json")
    path.write_text(json.dumps(oracle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(oracle, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
