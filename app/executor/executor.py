from typing import TYPE_CHECKING

from app.executor.context import ExecutionContext
from app.executor.engine import PandasExecutionEngine
from app.executor.models import ExecutionResult
from app.knowledge.models import KnowledgeContext
from app.planner.models import ExecutionPlan

if TYPE_CHECKING:
    import pandas as pd


class TerbieExecutor:
    """Executes declarative ExecutionPlans using the configured engine."""

    def __init__(self, engine: PandasExecutionEngine) -> None:
        self._engine = engine

    def execute(
        self,
        *,
        dataframe: "pd.DataFrame",
        plan: ExecutionPlan,
        knowledge_context: KnowledgeContext,
    ) -> ExecutionResult:
        return self._engine.execute(
            dataframe=dataframe,
            plan=plan,
            context=ExecutionContext(knowledge_context=knowledge_context),
        )
