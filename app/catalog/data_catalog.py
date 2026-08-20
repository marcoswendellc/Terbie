import json
from pathlib import Path

from app.models.schema import DataCatalogEntry, TableSchema


class DataCatalog:
    """In-memory structural catalog for loaded data tables."""

    def __init__(self) -> None:
        self._entries: dict[str, DataCatalogEntry] = {}
        self._dimension_values: dict[tuple[str, str], list[str]] = {}

    def register_table(self, entry: DataCatalogEntry) -> None:
        self._entries[entry.table_name] = entry

    def list_tables(self, datasource_name: str | None = None) -> list[str]:
        if datasource_name is None:
            return sorted(self._entries)

        return sorted(
            table_name
            for table_name, entry in self._entries.items()
            if entry.datasource_name == datasource_name
        )

    def get_schema(
        self,
        table_name: str,
        datasource_name: str | None = None,
    ) -> TableSchema | None:
        entry = self._entries.get(table_name)
        if entry is None:
            return None
        if datasource_name is not None and entry.datasource_name != datasource_name:
            return None

        return entry.table_schema

    def get_entry(
        self,
        table_name: str,
        datasource_name: str | None = None,
    ) -> DataCatalogEntry | None:
        entry = self._entries.get(table_name)
        if entry is None:
            return None
        if datasource_name is not None and entry.datasource_name != datasource_name:
            return None
        return entry

    def register_dimension_values(
        self,
        *,
        table_name: str,
        column: str,
        values: list[str],
    ) -> None:
        self._dimension_values[(table_name, column)] = sorted(
            dict.fromkeys(value for value in values if value.strip()),
        )

    def dimension_values(self, *, table_name: str, column: str) -> list[str]:
        return list(self._dimension_values.get((table_name, column), []))

    def best_table_for_columns(self, required_columns: set[str]) -> str | None:
        candidates = [
            entry
            for entry in self._entries.values()
            if required_columns.issubset(
                {column.name for column in entry.table_schema.columns},
            )
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda entry: entry.table_schema.row_count).table_name

    def quality_profile(self, table_name: str) -> dict[str, object] | None:
        schema = self.get_schema(table_name)
        if schema is None:
            return None
        row_count = schema.row_count
        columns = [
            {
                "name": column.name,
                "data_type": column.data_type,
                "null_count": column.null_count,
                "completeness": (
                    round(1 - column.null_count / row_count, 4) if row_count else 0.0
                ),
                "unique_count": column.unique_count,
            }
            for column in schema.columns
        ]
        return {
            "table": table_name,
            "row_count": row_count,
            "column_count": len(schema.columns),
            "columns": columns,
        }

    def persist(self, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "entries": [entry.model_dump(mode="json") for entry in self._entries.values()],
            "dimension_values": [
                {"table": table, "column": column, "values": values}
                for (table, column), values in self._dimension_values.items()
            ],
        }
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def restore(self, path: str) -> bool:
        target = Path(path)
        if not target.exists():
            return False
        payload = json.loads(target.read_text(encoding="utf-8"))
        self._entries = {
            entry.table_name: entry
            for raw in payload.get("entries", [])
            if isinstance(raw, dict)
            for entry in [DataCatalogEntry.model_validate(raw)]
        }
        self._dimension_values = {
            (str(item["table"]), str(item["column"])): [
                str(value) for value in item.get("values", [])
            ]
            for item in payload.get("dimension_values", [])
            if isinstance(item, dict) and "table" in item and "column" in item
        }
        return True
