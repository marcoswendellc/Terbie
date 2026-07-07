from typing import Protocol

from app.executor.models import ExecutionResult
from app.insights.models import InsightResult


class InsightAnalyzer(Protocol):
    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        raise NotImplementedError


class InsightAnalyzerFactory:
    def __init__(self, analyzers: dict[str, InsightAnalyzer]) -> None:
        self._analyzers = analyzers

    def analyzer_for(self, intent: str | None) -> InsightAnalyzer | None:
        return self._analyzers.get(intent)
