import json
from pathlib import Path

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.entity_resolution.entity_resolver import EntityResolver
from app.evaluation.models import EvaluationCase, evaluate_case
from app.knowledge.knowledge_service import KnowledgeService
from app.metrics.metric_resolver import MetricResolver
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver


def _compile(question: str):
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(metric_resolver=MetricResolver()),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        entity_resolver=EntityResolver(),
    )
    return compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=SemanticResolver().resolve(question),
            knowledge_context=KnowledgeService().get_context(),
        ),
    )


def test_business_language_evaluation_set() -> None:
    cases = json.loads(Path("evals/business_questions.json").read_text(encoding="utf-8"))
    results = [evaluate_case(EvaluationCase.model_validate(case), _compile) for case in cases]

    assert all(result.passed for result in results), [result.failures for result in results]
