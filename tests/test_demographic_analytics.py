from datetime import date

import pandas as pd

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.models import AnalyticalHypothesis, AnalyticalPlan
from app.executor.context import ExecutionContext
from app.executor.operations.derive_demographics import DeriveDemographicsOperation
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.models import PlanOperation
from app.semantic.resolver import SemanticResolver
from app.services.execution_service import ExecutionService


def test_demographics_normalize_gender_and_derive_age_bands() -> None:
    current_year = date.today().year
    dataframe = pd.DataFrame(
        {
            "cd_sexo": ["F", 0, "M", 1, "O", None],
            "dt_nascimento": [
                f"01/01/{current_year - 17}",
                f"01/01/{current_year - 24}",
                f"01/01/{current_year - 34}",
                f"01/01/{current_year - 44}",
                f"01/01/{current_year - 59}",
                None,
            ],
        },
    )
    context = ExecutionContext(knowledge_context=KnowledgeService().get_context())

    result = DeriveDemographicsOperation().execute(
        dataframe,
        PlanOperation(type="derive_demographics"),
        context,
    )

    assert result["genero"].tolist() == [
        "Feminino",
        "Feminino",
        "Masculino",
        "Masculino",
        "Outros",
        "Não informado",
    ]
    assert result["faixa_etaria"].tolist() == [
        "0-17",
        "18-24",
        "25-34",
        "35-44",
        "45-59",
        "Não informado",
    ]


def test_gender_visit_question_defaults_to_unique_visitors() -> None:
    interpretation = SemanticResolver().resolve(
        "Qual gênero mais visita o shopping?",
    ).interpretation

    assert interpretation is not None
    assert interpretation.intent == "ranking"
    assert interpretation.entity == "genero"
    assert interpretation.dimensions == ["genero"]
    assert interpretation.metrics == ["clientes_unicos"]


def test_persona_question_groups_gender_and_age_band() -> None:
    interpretation = SemanticResolver().resolve(
        "Crie uma persona do público que visita o shopping",
    ).interpretation

    assert interpretation is not None
    assert interpretation.intent == "ranking"
    assert interpretation.dimensions == ["genero", "faixa_etaria"]
    assert interpretation.metrics == ["clientes_unicos"]

    plan = ExecutionPlanBuilder().build(
        AnalyticalPlan(
            intent="ranking",
            entities=["genero"],
            metrics=["clientes_unicos"],
            dimensions=interpretation.dimensions,
            required_operations=["group_by", "aggregate", "sort"],
        ),
    )
    assert [operation.type for operation in plan.operations] == [
        "derive_demographics",
        "group_by",
        "aggregate",
        "sort",
    ]


def test_required_columns_use_demographic_sources_instead_of_derived_outputs() -> None:
    plan = ExecutionPlanBuilder().build(
        AnalyticalPlan(
            intent="ranking",
            entities=["promocao"],
            metrics=["clientes_unicos"],
            dimensions=["genero"],
            filters=[
                {"type": "filter", "field": "cd_promocao", "operator": "not_null"},
                {
                    "type": "filter",
                    "field": "sk_dtinicio",
                    "operator": "year_overlap",
                    "value": 2026,
                    "end_field": "sk_dtfim",
                },
            ],
            required_operations=["filter", "group_by", "aggregate", "sort", "limit"],
        ),
    )
    service = object.__new__(ExecutionService)

    required = service._required_columns(
        plan=plan,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert "cd_sexo" in required
    assert "genero" not in required
    assert {"sk_cliente", "cd_promocao", "sk_dtinicio", "sk_dtfim"}.issubset(required)


def test_campaign_context_does_not_replace_gender_as_the_analysis_entity() -> None:
    plan = AnalyticalPlanner().build(
        hypothesis=AnalyticalHypothesis(
            analysis_type="ranking",
            business_entity="promocao",
            metric="clientes_unicos",
            metrics=["clientes_unicos"],
            dimensions=["genero"],
            filters=[
                {"type": "filter", "field": "cd_promocao", "operator": "not_null"},
            ],
        ),
        knowledge_context=KnowledgeService().get_context(),
    )

    assert plan.entities == ["genero"]
    assert plan.dimensions == ["genero"]
    assert plan.filters[0]["field"] == "cd_promocao"
