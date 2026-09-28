import pandas as pd


def date_series(series: pd.Series) -> pd.Series:
    """Parse dimension dates without ordering Brazilian dates lexicographically."""
    raw = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    compact = raw.str.fullmatch(r"\d{8}", na=False)
    serial = raw.str.fullmatch(r"\d{5}(?:\.\d+)?", na=False)
    iso = raw.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", na=False)
    parsed.loc[compact] = pd.to_datetime(raw.loc[compact], format="%Y%m%d", errors="coerce")
    parsed.loc[serial] = pd.to_datetime(
        pd.to_numeric(raw.loc[serial]), unit="D", origin="1899-12-30", errors="coerce"
    )
    parsed.loc[iso] = pd.to_datetime(
        raw.loc[iso].str.extract(r"^(\d{4}[-/]\d{1,2}[-/]\d{1,2})", expand=False),
        format="mixed",
        dayfirst=False,
        errors="coerce",
    )
    other = ~(compact | serial | iso)
    parsed.loc[other] = pd.to_datetime(
        raw.loc[other], format="mixed", dayfirst=True, errors="coerce"
    )
    return parsed
