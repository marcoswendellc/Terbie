from app.executor.models import ExecutionResult
from app.insights.anomaly import AnomalyInsightAnalyzer
from app.insights.campaign_detail import CampaignDetailInsightAnalyzer
from app.insights.comparison import ComparisonInsightAnalyzer
from app.insights.factory import InsightAnalyzerFactory
from app.insights.listing import ListingInsightAnalyzer
from app.insights.metric import MetricInsightAnalyzer
from app.insights.models import InsightResult
from app.insights.ranking import RankingInsightAnalyzer
from app.insights.trend import TrendInsightAnalyzer


class InsightGenerator:
    _ANALYSIS_TERMS = (
        "analise",
        "analisa",
        "analisar",
        "desempenho",
        "resumo executivo",
        "principais insights",
        "insights",
        "o que voce percebe",
        "o que percebe",
    )

    def __init__(self, factory: InsightAnalyzerFactory | None = None) -> None:
        self._factory = factory or InsightAnalyzerFactory(
            analyzers={
                "comparison": ComparisonInsightAnalyzer(),
                "campaign_detail": CampaignDetailInsightAnalyzer(),
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
        question = str(execution_result.metadata.get("question", ""))
        if intent in {"ranking", "list_distinct"} and question and not self._asks_for_analysis(
            question,
        ):
            return InsightResult()

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

    def _asks_for_analysis(self, question: str) -> bool:
        normalized = self._normalize_text(question)
        return any(term in normalized for term in self._ANALYSIS_TERMS)

    def _normalize_text(self, text: str) -> str:
        replacements = {
            "á": "a",
            "à": "a",
            "â": "a",
            "ã": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }
        normalized = text.lower()
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return normalized
