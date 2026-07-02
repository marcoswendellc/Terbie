from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import AnalyticalHypothesis, CompilerRequest
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.reasoning.base import BaseReasoningProvider
from app.reasoning.models import ReasoningContext, ReasoningResult
from app.semantic.resolver import SemanticResolver


class SuccessfulReasoningProvider(BaseReasoningProvider):
    def generate_hypothesis(self, context: ReasoningContext) -> ReasoningResult:
        _ = context
        return ReasoningResult(
            hypothesis=AnalyticalHypothesis(
                goal="identificar melhores resultados",
                analysis_type="ranking",
                business_entity="loja",
                metric="ticket_medio",
                time_scope="current_month",
                confidence=0.9,
                warnings=[],
            ),
            raw_response="{}",
            warnings=[],
            provider="test",
            model="fake",
            success=True,
        )


class FailingReasoningProvider(BaseReasoningProvider):
    def generate_hypothesis(self, context: ReasoningContext) -> ReasoningResult:
        _ = context
        return ReasoningResult(
            hypothesis=None,
            raw_response=None,
            warnings=["falha simulada"],
            provider="test",
            model="fake",
            success=False,
        )


def _compiler(provider: BaseReasoningProvider) -> TerbieCompiler:
    return TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        reasoning_provider=provider,
    )


def _request(question: str) -> CompilerRequest:
    return CompilerRequest(
        question=question,
        semantic_resolution=SemanticResolver().resolve(question),
        knowledge_context=KnowledgeService().get_context(),
    )


def test_compiler_uses_valid_reasoning_hypothesis() -> None:
    response = _compiler(SuccessfulReasoningProvider()).compile(
        _request("Qual o ticket médio das lojas este mês?"),
    )

    assert response.hypothesis.metric == "ticket_medio"
    assert response.hypothesis.business_entity == "loja"
    assert response.hypothesis.time_scope == "current_month"


def test_compiler_falls_back_when_reasoning_fails() -> None:
    response = _compiler(FailingReasoningProvider()).compile(
        _request("Quais são os 10 restaurantes com maior faturamento?"),
    )

    assert response.hypothesis.metric == "faturamento"
    assert response.hypothesis.business_entity == "restaurante"
    assert "ReasoningProvider falhou; fallback determinístico utilizado." in response.warnings
