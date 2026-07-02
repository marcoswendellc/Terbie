from app.core.exceptions import DataSourceError
from app.datasources.base import BaseDataSource


class DataSourceRegistry:
    """Registry for configured data sources."""

    def __init__(self, *, default_name: str) -> None:
        self._default_name = default_name
        self._datasources: dict[str, BaseDataSource] = {}

    def register(self, name: str, datasource: BaseDataSource) -> None:
        self._datasources[name] = datasource

    def get(self, name: str) -> BaseDataSource:
        datasource = self._datasources.get(name)
        if datasource is None:
            raise DataSourceError(
                "Data source is not registered",
                details={"datasource_name": name},
            )
        return datasource

    def list(self) -> list[BaseDataSource]:
        return [self._datasources[name] for name in sorted(self._datasources)]

    def default(self) -> BaseDataSource:
        return self.get(self._default_name)

    def exists(self, name: str) -> bool:
        return name in self._datasources

    @property
    def default_name(self) -> str:
        return self._default_name
