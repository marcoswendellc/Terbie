from app.executor.models import ExecutionResult
from app.insights.anomaly import AnomalyInsightAnalyzer
from app.insights.comparison import ComparisonInsightAnalyzer
from app.insights.factory import InsightAnalyzerFactory
from app.insights.listing import ListingInsightAnalyzer
from app.insights.metric import MetricInsightAnalyzer
from app.insights.models import InsightResult
from app.insights.ranking import RankingInsightAnalyzer
from app.insights.trend import TrendInsightAnalyzer


class InsightGenerator:
    def __init__(self, factory: InsightAnalyzerFactory | None = None) -> None:
        self._factory = factory or InsightAnalyzerFactory(
            analyzers={
                "comparison": ComparisonInsightAnalyzer(),
                "ranking": RankingInsightAnalyzer(),
                "list_distinct": ListingInsightAnalyzer(),
                "trend": TrendInsightAnalyzer(),
                "growth": TrendInsightAnalyzer(),
                "anomaly": AnomalyInsightAnalyzer(),
            },
        )
        self._metric_analyzer = MetricInsightAnalyzer()

    def generate(
        self,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        intent = getattr(execution_plan, "intent", None)
        analyzer = self._factory.analyzer_for(intent)
        if analyzer is not None:
            return analyzer.generate(
                execution_result=execution_result,
                analytical_plan=analytical_plan,
                execution_plan=execution_plan,
            )

        return self._metric_analyzer.generate(
            execution_result=execution_result,
            analytical_plan=analytical_plan,
            execution_plan=execution_plan,
        )
