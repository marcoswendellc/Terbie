from app.executor.models import ExecutionResult
from app.insights.models import InsightResult


class TrendInsightAnalyzer:
    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = execution_result, analytical_plan, execution_plan
        return InsightResult(summary="Análise de tendência ainda não implementada.")
