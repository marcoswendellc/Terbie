import pandas as pd

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.context_resolution.context_resolver import ContextResolver
from app.entity_resolution.entity_resolver import EntityResolver
from app.executor.engine import PandasExecutionEngine
from app.executor.executor import TerbieExecutor
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.knowledge.knowledge_service import KnowledgeService
from app.metrics.metric_resolver import MetricResolver
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarratorRequest
from app.narrator.narrator import TerbieNarrator
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver


def test_sales_availability_question_returns_real_date_range() -> None:
    question = "Você possui venda a partir de que data?"
    semantic_resolution = SemanticResolver().resolve(question)
    entity_resolver = EntityResolver()
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(metric_resolver=MetricResolver()),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        entity_resolver=entity_resolver,
        context_resolver=ContextResolver(
            entity_resolver=entity_resolver,
            metric_resolver=MetricResolver(),
        ),
    )
    compiled = compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=KnowledgeService().get_context(),
        ),
    )

    assert compiled.execution_plan.intent == "sales_date_range"

    executor = TerbieExecutor(
        engine=PandasExecutionEngine(
            pipeline_executor=PipelineExecutor(registry=OperationRegistry()),
        ),
    )
    result = executor.execute(
        dataframe=pd.DataFrame(
            {"dt_registro_mos": ["2025-03-15", "2024-01-10", "2026-07-30"]},
        ),
        plan=compiled.execution_plan,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert result.data == [
        {"primeira_venda": "2024-01-10", "ultima_venda": "2026-07-30"},
    ]

    response = TerbieNarrator(
        context_builder=NarrativeContextBuilder(),
        formatter=NarrativeFormatter(),
    ).narrate(
        NarratorRequest(
            question=question,
            execution_result=result,
            execution_plan=compiled.execution_plan,
        ),
    )

    assert response.answer == "Há vendas disponíveis de 10/01/2024 até 30/07/2026."
