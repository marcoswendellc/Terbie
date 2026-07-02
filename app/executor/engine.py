from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.models import ExecutionResult
from app.executor.pipeline import PipelineExecutor
from app.planner.models import ExecutionPlan

if TYPE_CHECKING:
    import pandas as pd


class PandasExecutionEngine:
    """Applies a pipeline over Pandas DataFrames."""

    def __init__(self, pipeline_executor: PipelineExecutor) -> None:
        self._pipeline_executor = pipeline_executor

    def execute(
        self,
        *,
        dataframe: "pd.DataFrame",
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> ExecutionResult:
        return self._pipeline_executor.execute(
            dataframe=dataframe,
            plan=plan,
            context=context,
        )
