from datetime import date

import pandas as pd

from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.models import AnalyticalPlan
from app.executor.context import ExecutionContext
from app.executor.operations.derive_demographics import DeriveDemographicsOperation
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.models import PlanOperation
from app.semantic.resolver import SemanticResolver


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
