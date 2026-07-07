from decimal import ROUND_HALF_UP, Decimal


class NarrativeFormatter:
    """Formats values for deterministic Portuguese narratives."""

    def currency_brl(self, value: int | float | Decimal) -> str:
        decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        integer_part, decimal_part = f"{decimal_value:.2f}".split(".")
        formatted_integer = f"{int(integer_part):,}".replace(",", ".")
        return f"R$ {formatted_integer},{decimal_part}"

    def integer(self, value: int | float) -> str:
        return f"{int(value):,}".replace(",", ".")

    def percent(self, value: int | float) -> str:
        return f"{value * 100:.2f}%".replace(".", ",")

    def value(self, column: str, value: object) -> str:
        if isinstance(value, int | float) and self._looks_like_money(column):
            return self.currency_brl(value)

        if isinstance(value, int | float):
            return self.integer(value) if float(value).is_integer() else str(round(float(value), 2))

        return str(value)

    def ranking_text(self, *, dimension: str, metric: str) -> str:
        return f"{dimension}, com {metric}"

    def _looks_like_money(self, column: str) -> bool:
        return column in {
            "faturamento",
            "vl_compra",
            "receita",
            "valor",
            "ticket_medio",
            "ticket_medio_por_compra",
            "ticket_medio_por_cliente",
        }
