import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

from app.executor.context import ExecutionContext
from app.executor.operations.base import BaseOperation
from app.planner.models import PlanOperation


class FilterOperation(BaseOperation):
    operation_type = "filter"

    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        field = context.resolve_dimension_column(operation.field)
        value = operation.parameters.get("value")
        operator = operation.parameters.get("operator", "equals")
        if field is None:
            context.warnings.append("Filtro sem campo definido.")
            return dataframe

        if field not in dataframe.columns:
            context.warnings.append(f"Campo de filtro não encontrado: {field}.")
            return dataframe

        if operator == "not_null":
            return dataframe[dataframe[field].notna()]

        if value is None:
            context.warnings.append("Filtro sem valor definido.")
            return dataframe

        if operator == "contains":
            return dataframe[
                dataframe[field].astype("string").str.contains(
                    str(value),
                    case=False,
                    na=False,
                    regex=False,
                )
            ]

        if operator == "entity_match":
            requested = self._normalize(str(value))
            candidates = dataframe[field].dropna().astype("string").unique().tolist()
            scored = [
                (
                    self._entity_similarity(
                        self._match_text(requested, field),
                        self._match_text(self._normalize(candidate), field),
                    ),
                    candidate,
                )
                for candidate in candidates
            ]
            if not scored:
                return dataframe.iloc[0:0]

            score, selected = max(scored, key=lambda item: item[0])
            if score < 0.6:
                context.warnings.append(
                    f"Empreendimento não encontrado para o termo informado: {value}.",
                )
                return dataframe.iloc[0:0]

            context.metadata.setdefault("resolved_entities", {})[field] = selected
            return dataframe[dataframe[field].astype("string") == selected]

        if operator == "in":
            if not isinstance(value, list):
                context.warnings.append("Filtro in sem lista de valores.")
                return dataframe

            return dataframe[dataframe[field].isin(value)]

        if operator == "year_overlap":
            end_field = operation.parameters.get("end_field")
            if not isinstance(value, int) or not isinstance(end_field, str):
                context.warnings.append("Filtro de ano sem período de promoção definido.")
                return dataframe

            if end_field not in dataframe.columns:
                context.warnings.append(f"Campo de fim de período não encontrado: {end_field}.")
                return dataframe

            return dataframe[
                self._date_series(dataframe[field]).le(pd.Timestamp(year=value, month=12, day=31))
                & self._date_series(dataframe[end_field]).ge(
                    pd.Timestamp(year=value, month=1, day=1),
                )
            ]

        return dataframe[dataframe[field] == value]

    def _normalize(self, value: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(char)
        )
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", without_accents)).strip()

    def _entity_similarity(self, requested: str, candidate: str) -> float:
        if requested == candidate:
            return 1.0

        requested_tokens = set(requested.split())
        candidate_tokens = set(candidate.split())
        if len(requested_tokens) >= 2 and requested_tokens.issubset(candidate_tokens):
            return 0.95
        union = requested_tokens | candidate_tokens
        token_score = len(requested_tokens & candidate_tokens) / len(union) if union else 0.0
        sequence_score = SequenceMatcher(None, requested, candidate).ratio()
        return max(token_score, sequence_score)

    def _match_text(self, value: str, field: str) -> str:
        if field != "nm_promocao":
            return value
        ignored = {"a", "as", "campanha", "da", "das", "de", "do", "dos", "promocao"}
        return " ".join(token for token in value.split() if token not in ignored)

    def _date_series(self, series: "pd.Series") -> "pd.Series":
        normalized = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
        parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

        compact_mask = normalized.str.fullmatch(r"\d{8}", na=False)
        parsed.loc[compact_mask] = pd.to_datetime(
            normalized.loc[compact_mask],
            format="%Y%m%d",
            errors="coerce",
        )

        excel_serial_mask = normalized.str.fullmatch(r"\d{5}", na=False)
        parsed.loc[excel_serial_mask] = pd.to_datetime(
            pd.to_numeric(normalized.loc[excel_serial_mask], errors="coerce"),
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

        remaining_mask = parsed.isna() & normalized.notna()
        parsed.loc[remaining_mask] = pd.to_datetime(
            normalized.loc[remaining_mask],
            format="mixed",
            dayfirst=True,
            errors="coerce",
        )
        return parsed
