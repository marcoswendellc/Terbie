from app.executor.operations.aggregate import AggregateOperation
from app.executor.operations.base import BaseOperation
from app.executor.operations.derived_metric import DerivedMetricOperation
from app.executor.operations.distinct import DistinctOperation
from app.executor.operations.filter import FilterOperation
from app.executor.operations.group_by import GroupByOperation
from app.executor.operations.limit import LimitOperation
from app.executor.operations.select import SelectOperation
from app.executor.operations.sort import SortOperation


class OperationRegistry:
    """Registry of executable operation handlers."""

    def __init__(self) -> None:
        self._operations: dict[str, BaseOperation] = {}
        self.register(FilterOperation())
        self.register(SelectOperation())
        self.register(DistinctOperation())
        self.register(GroupByOperation())
        self.register(AggregateOperation())
        self.register(DerivedMetricOperation())
        self.register(SortOperation())
        self.register(LimitOperation())

    def register(self, operation: BaseOperation) -> None:
        self._operations[operation.operation_type] = operation

    def get(self, operation_type: str) -> BaseOperation | None:
        return self._operations.get(operation_type)
