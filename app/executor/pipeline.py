from time import perf_counter
from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.models import ExecutionResult
from app.executor.registry import OperationRegistry
from app.planner.models import ExecutionPlan

if TYPE_CHECKING:
    import pandas as pd


class PipelineExecutor:
    """Executes an ExecutionPlan through registered operations."""

    def __init__(self, registry: OperationRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        *,
        dataframe: "pd.DataFrame",
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> ExecutionResult:
        start = perf_counter()
        result_frame = dataframe.copy()

        for operation in plan.operations:
            handler = self._registry.get(operation.type)
            if handler is None:
                context.warnings.append(f"Operação não registrada: {operation.type}.")
                continue

            result_frame = handler.execute(result_frame, operation, context)

        execution_time = perf_counter() - start
        records = result_frame.to_dict(orient="records")
        return ExecutionResult(
            data=records,
            metadata={
                "plan_version": plan.version,
                "operations": [operation.type for operation in plan.operations],
                **context.metadata,
            },
            statistics={
                "rows_input": len(dataframe),
                "rows_output": len(result_frame),
            },
            warnings=[*plan.warnings, *context.warnings],
            execution_time=execution_time,
            rows_returned=len(result_frame),
        )
