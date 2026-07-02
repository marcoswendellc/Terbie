from app.models.schema import DataCatalogEntry, TableSchema


class DataCatalog:
    """In-memory structural catalog for loaded data tables."""

    def __init__(self) -> None:
        self._entries: dict[str, DataCatalogEntry] = {}

    def register_table(self, entry: DataCatalogEntry) -> None:
        self._entries[entry.table_name] = entry

    def list_tables(self) -> list[str]:
        return sorted(self._entries)

    def get_schema(self, table_name: str) -> TableSchema | None:
        entry = self._entries.get(table_name)
        if entry is None:
            return None

        return entry.table_schema

    def get_entry(self, table_name: str) -> DataCatalogEntry | None:
        return self._entries.get(table_name)
