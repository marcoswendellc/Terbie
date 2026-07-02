from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.planner.models import PlanOperation

if TYPE_CHECKING:
    import pandas as pd


class BaseOperation(ABC):
    operation_type: str

    @abstractmethod
    def execute(
        self,
        dataframe: "pd.DataFrame",
        operation: PlanOperation,
        context: ExecutionContext,
    ) -> "pd.DataFrame":
        raise NotImplementedError
