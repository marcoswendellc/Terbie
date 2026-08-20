from datetime import date

import pandas as pd

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.models import AnalyticalHypothesis, AnalyticalPlan
from app.executor.context import ExecutionContext
from app.executor.operations.derive_demographics import DeriveDemographicsOperation
from app.executor.operations.persona_profile import (
    PersonaComparisonOperation,
    PersonaProfileOperation,
)
from app.context_resolution.context_resolver import ContextResolver
from app.entity_resolution.entity_resolver import EntityResolver
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.formatter import NarrativeFormatter
from app.narrator.models import NarrativeContext
from app.narrator.strategies import PersonaStrategy, RankingStrategy
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
    assert interpretation.intent == "persona"
    assert interpretation.dimensions == ["genero", "faixa_etaria"]
    assert interpretation.metrics == ["clientes_unicos"]

    plan = ExecutionPlanBuilder().build(
        AnalyticalPlan(
            intent="persona",
            entities=["genero"],
            metrics=["clientes_unicos"],
            dimensions=interpretation.dimensions,
            required_operations=["persona_profile"],
        ),
    )
    assert [operation.type for operation in plan.operations] == [
        "derive_demographics",
        "persona_profile",
    ]


def test_persona_profile_uses_unique_visitors_and_independent_percentages() -> None:
    dataframe = pd.DataFrame(
        {
            "sk_cliente": [1, 1, 2, 3, 4],
            "genero": ["Feminino", "Feminino", "Feminino", "Masculino", "Feminino"],
            "faixa_etaria": ["25-34", "25-34", "25-34", "35-44", "18-24"],
            "cidade": ["Goiânia", "Goiânia", "Goiânia", "Aparecida", "Goiânia"],
        },
    )
    context = ExecutionContext(knowledge_context=KnowledgeService().get_context())

    result = PersonaProfileOperation().execute(
        dataframe,
        PlanOperation(type="persona_profile"),
        context,
    )

    row = result.iloc[0].to_dict()
    assert row["genero_predominante"] == "Feminino"
    assert row["percentual_genero"] == 0.75
    assert row["quantidade_genero"] == 3
    assert row["faixa_etaria_predominante"] == "25-34"
    assert row["percentual_faixa_etaria"] == 0.5
    assert row["quantidade_faixa_etaria"] == 2
    assert row["localidade_predominante"] == "Goiânia"
    assert row["percentual_localidade"] == 0.75
    assert row["quantidade_localidade"] == 3
    assert row["clientes_unicos"] == 4


def test_persona_narrative_uses_requested_shopping_and_dominant_profile() -> None:
    context = NarrativeContext(
        question="Chat, consegue me definir uma persona do Buriti Shopping?",
        rows_returned=1,
        data=[],
        top_row={
            "genero_predominante": "Feminino",
            "percentual_genero": 0.62,
            "faixa_etaria_predominante": "25-34",
            "percentual_faixa_etaria": 0.41,
            "localidade_predominante": "Goiânia",
            "percentual_localidade": 0.55,
        },
        intent="persona",
    )

    answer = PersonaStrategy(NarrativeFormatter()).answer(context)

    assert "Buriti Shopping" in answer
    assert "gênero Feminino (62,00%)" in answer
    assert "25-34 (41,00%)" in answer
    assert "Goiânia (55,00%)" in answer
    assert "605" not in answer
    assert "números absolutos" not in answer


def test_persona_intent_overrides_external_ranking_hypothesis() -> None:
    compiler = object.__new__(TerbieCompiler)
    compiler._context_resolver = ContextResolver()
    external_hypothesis = AnalyticalHypothesis(
        analysis_type="ranking",
        business_entity="genero",
        metric="clientes_unicos",
        metrics=["clientes_unicos"],
        dimensions=["genero", "faixa_etaria"],
    )

    normalized = compiler._normalize_persona_question(
        question="Defina uma persona do Buriti Shopping",
        hypothesis=external_hypothesis,
    )

    assert normalized.analysis_type == "persona"


def test_persona_for_shopping_does_not_add_campaign_name_as_a_filter() -> None:
    compiler = object.__new__(TerbieCompiler)
    compiler._entity_resolver = EntityResolver()
    compiler._context_resolver = ContextResolver(entity_resolver=compiler._entity_resolver)

    hypothesis = compiler._apply_entity_resolution(
        question="Defina uma persona do Buriti Shopping",
        hypothesis=AnalyticalHypothesis(
            analysis_type="persona",
            business_entity="genero",
            metric="clientes_unicos",
            metrics=["clientes_unicos"],
            dimensions=["genero", "faixa_etaria"],
        ),
    )

    assert [filter_item["field"] for filter_item in hypothesis.filters] == [
        "nm_empreendimento",
    ]


def test_persona_locality_columns_are_optional_for_dataframe_selection() -> None:
    plan = ExecutionPlanBuilder().build(
        AnalyticalPlan(
            intent="persona",
            entities=["genero", "faixa_etaria"],
            metrics=["clientes_unicos"],
            dimensions=["genero", "faixa_etaria"],
            filters=[
                {
                    "type": "filter",
                    "field": "nm_empreendimento",
                    "operator": "equals",
                    "value": "Buriti Shopping",
                },
            ],
            required_operations=["filter", "persona_profile"],
        ),
    )
    service = object.__new__(ExecutionService)

    required = service._required_columns(
        plan=plan,
        knowledge_context=KnowledgeService().get_context(),
    )

    assert required == {
        "cd_sexo",
        "dt_nascimento",
        "nm_empreendimento",
        "sk_cliente",
    }


def test_persona_comparison_is_forced_for_plural_shopping_request() -> None:
    compiler = object.__new__(TerbieCompiler)
    compiler._context_resolver = ContextResolver()

    normalized = compiler._normalize_persona_question(
        question="Faça um quadro comparativo de persona entre os shoppings",
        hypothesis=AnalyticalHypothesis(analysis_type="ranking"),
    )

    assert normalized.analysis_type == "persona_comparison"
    assert normalized.business_entity == "empreendimento"


def test_persona_comparison_calculates_one_percentage_profile_per_shopping() -> None:
    dataframe = pd.DataFrame(
        {
            "nm_empreendimento": ["Shopping A", "Shopping A", "Shopping B", "Shopping B"],
            "sk_cliente": [1, 2, 3, 4],
            "genero": ["Feminino", "Feminino", "Masculino", "Feminino"],
            "faixa_etaria": ["25-34", "35-44", "18-24", "18-24"],
            "cidade": ["NULL", "Goiânia", "Anápolis", "Anápolis"],
        },
    )
    context = ExecutionContext(knowledge_context=KnowledgeService().get_context())

    result = PersonaComparisonOperation().execute(
        dataframe,
        PlanOperation(type="persona_comparison"),
        context,
    )

    shopping_a = result.set_index("nm_empreendimento").loc["Shopping A"]
    assert shopping_a["genero_predominante"] == "Feminino"
    assert shopping_a["percentual_genero"] == 1.0
    assert shopping_a["localidade_predominante"] == "Goiânia"
    assert shopping_a["percentual_localidade"] == 1.0


def test_persona_comparison_narrative_is_a_percentage_table() -> None:
    context = NarrativeContext(
        question="Faça um quadro comparativo de persona entre os shoppings",
        rows_returned=1,
        data=[
            {
                "nm_empreendimento": "Shopping A",
                "genero_predominante": "Feminino",
                "percentual_genero": 0.7,
                "faixa_etaria_predominante": "25-34",
                "percentual_faixa_etaria": 0.4,
                "localidade_predominante": "Goiânia",
                "percentual_localidade": 0.6,
            },
        ],
        top_row={},
        intent="persona_comparison",
    )

    answer = PersonaStrategy(NarrativeFormatter()).answer(context)

    assert "| Shopping | Gênero predominante | % gênero |" in answer
    assert "| Shopping A | Feminino | 70,00% | 25-34 | 40,00% | Goiânia | 60,00% |" in answer


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


def test_purchase_quantity_and_value_by_gender_resolve_both_metrics() -> None:
    interpretation = SemanticResolver().resolve(
        "Qual foi a quantidade de compras e valor das compras por gênero?",
    ).interpretation

    assert interpretation is not None
    assert interpretation.entity == "genero"
    assert interpretation.dimensions == ["genero"]
    assert interpretation.metrics == ["quantidade_compras", "faturamento"]

    plan = ExecutionPlanBuilder().build(
        AnalyticalPlan(
            intent="ranking",
            entities=["genero"],
            metrics=interpretation.metrics,
            dimensions=interpretation.dimensions,
            required_operations=["group_by", "aggregate", "sort"],
        ),
    )
    aggregate = next(operation for operation in plan.operations if operation.type == "aggregate")
    aliases = [metric["alias"] for metric in aggregate.parameters["metrics"]]
    assert aliases == ["quantidade_compras", "faturamento"]


def test_gender_ranking_narrative_displays_purchase_quantity_and_value() -> None:
    context = NarrativeContext(
        question="Qual foi a quantidade de compras e valor das compras por gênero?",
        rows_returned=2,
        data=[
            {"genero": "Feminino", "quantidade_compras": 57654, "faturamento": 123456.78},
            {"genero": "Masculino", "quantidade_compras": 20191, "faturamento": 65432.10},
        ],
        columns=["genero", "quantidade_compras", "faturamento"],
        top_row={
            "genero": "Feminino",
            "quantidade_compras": 57654,
            "faturamento": 123456.78,
        },
        metric_columns=["quantidade_compras", "faturamento"],
        dimension_columns=["genero"],
        intent="ranking",
    )

    answer = RankingStrategy(NarrativeFormatter()).answer(context)

    assert "Quantidade de compras: 57.654" in answer
    assert "Valor das compras: R$ 123.456,78" in answer
