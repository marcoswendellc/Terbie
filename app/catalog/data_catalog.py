from app.models.schema import DataCatalogEntry, TableSchema


class DataCatalog:
    """In-memory structural catalog for loaded data tables."""

    def __init__(self) -> None:
        self._entries: dict[str, DataCatalogEntry] = {}

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
