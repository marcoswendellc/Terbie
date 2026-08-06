from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def numeric_series(series: "pd.Series") -> "pd.Series":
    """Converts numbers formatted by Google Sheets in pt-BR or neutral notation."""
    import pandas as pd

    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    text = (
        series.astype("string")
        .str.strip()
        .str.replace("\u00a0", "", regex=False)
        .str.replace(r"^R\$\s*", "", regex=True)
        .str.replace(r"\s+", "", regex=True)
    )
    negative_parentheses = text.str.match(r"^\(.*\)$", na=False)
    text = text.str.replace(r"^\((.*)\)$", r"\1", regex=True)

    has_comma = text.str.contains(",", regex=False, na=False)
    normalized = text.copy()
    normalized.loc[has_comma] = (
        normalized.loc[has_comma]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    values = pd.to_numeric(normalized, errors="coerce")
    values.loc[negative_parentheses] = -values.loc[negative_parentheses].abs()
    return values
