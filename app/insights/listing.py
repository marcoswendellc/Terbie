from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult


class ListingInsightAnalyzer:
    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = analytical_plan, execution_plan
        count = execution_result.rows_returned
        columns = list(execution_result.data[0]) if execution_result.data else []
        insight = Insight(
            id="listing_count",
            type="listing",
            title="Quantidade encontrada",
            description=f"A listagem retornou {count} item(ns) distintos.",
            value=count,
            metadata={"columns": columns},
        )
        return InsightResult(
            insights=[insight],
            summary=insight.description,
            recommendations=["Filtrar por período", "Comparar itens", "Detalhar por categoria"],
        )
