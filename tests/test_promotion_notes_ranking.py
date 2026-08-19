import pandas as pd

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.executor.engine import PandasExecutionEngine
from app.executor.executor import TerbieExecutor
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.intelligence import BaseNarrativeProvider, IntelligentNarrative
from app.narrator.models import NarratorRequest
from app.narrator.narrator import TerbieNarrator
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver

QUESTION = "Qual o top 10 de promoções por notas cadastradas?"


class IncorrectGenerativeNarrator(BaseNarrativeProvider):
    def generate(self, context) -> IntelligentNarrative:
        _ = context
        return IntelligentNarrative(answer="Resposta alterada pelo modelo")


def _plan():
    semantic = SemanticResolver().resolve(QUESTION)
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
    )
    return compiler.compile(
        CompilerRequest(
            question=QUESTION,
            semantic_resolution=semantic,
            knowledge_context=KnowledgeService().get_context(),
        ),
    ).execution_plan


def test_promotion_notes_ranking_counts_unique_notes_and_reports_short_result() -> None:
    plan = _plan()
    rows = []
    quantities = {"Promoção A": 4, "Promoção B": 3, "Promoção C": 2}
    for promotion, quantity in quantities.items():
        for note in range(quantity):
            # A duplicated source row must not count as an additional registered note.
            rows.extend(
                [
                    {
                        "cd_promocao": promotion,
                        "nm_promocao": promotion,
                        "cd_compra": f"{promotion}-{note}",
                    },
                    {
                        "cd_promocao": promotion,
                        "nm_promocao": promotion,
                        "cd_compra": f"{promotion}-{note}",
                    },
                ],
            )

    result = TerbieExecutor(
        engine=PandasExecutionEngine(
            pipeline_executor=PipelineExecutor(registry=OperationRegistry()),
        ),
    ).execute(
        dataframe=pd.DataFrame(rows),
        plan=plan,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert result.data == [
        {"nm_promocao": "Promoção A", "quantidade_compras": 4},
        {"nm_promocao": "Promoção B", "quantidade_compras": 3},
        {"nm_promocao": "Promoção C", "quantidade_compras": 2},
    ]
    assert result.metadata["executed_limit"] == 10
    assert result.metadata["rows_available_before_limit"] == 3

    response = TerbieNarrator(
        context_builder=NarrativeContextBuilder(),
        formatter=NarrativeFormatter(),
        intelligent_provider=IncorrectGenerativeNarrator(),
    ).narrate(
        NarratorRequest(
            question=QUESTION,
            execution_result=result,
            execution_plan=plan,
        ),
    )

    assert response.metadata["narrative_provider"] == "deterministic_ranking"
    assert response.answer.startswith(
        "Foram encontradas 3 campanhas com maior participação em volume de notas, "
        "de 10 solicitadas:",
    )
    assert "Contagem: notas únicas cadastradas (cd_compra distinto)." in response.answer
    assert "1. Promoção A — 4" in response.answer
    assert "Resposta alterada pelo modelo" not in response.answer
