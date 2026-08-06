import pandas as pd

from app.executor.numeric import numeric_series


def test_numeric_series_supports_brazilian_currency_and_neutral_numbers() -> None:
    values = pd.Series(["1.234,56", "R$ 10,44", "25.5", "(2,00)"])

    assert numeric_series(values).tolist() == [1234.56, 10.44, 25.5, -2.0]
