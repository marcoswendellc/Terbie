import pytest

from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.compiler.models import CompilerRequest
from app.entity_resolution.entity_resolver import EntityResolver
from app.knowledge.knowledge_service import KnowledgeService
from app.planner.optimizer import PlanOptimizer
from app.planner.validator import PlanValidator
from app.semantic.resolver import SemanticResolver

SHOPPING_NICKNAMES = [
    ("ALS", "Águas Lindas Shopping"),
    ("BPS", "Brasil Park Shopping"),
    ("BUR", "Buriti Shopping"),
    ("BRV", "Buriti Shopping Rio Verde"),
    ("GUA", "Buriti Shopping Guará"),
    ("MOG", "Buriti Shopping Mogi Guaçu"),
    ("POR", "Portal Shopping"),
    ("SHS", "Shopping Sul"),
]


@pytest.mark.parametrize("nickname,name", SHOPPING_NICKNAMES)
def test_shopping_nicknames_resolve_to_canonical_names(nickname, name):
    result = EntityResolver().resolve(f"Qual o faturamento do {nickname}?")
    assert not result.is_ambiguous
    assert [(match.field, match.value) for match in result.matches] == [
        ("nm_empreendimento", name),
    ]


def test_preposition_por_does_not_select_portal_shopping():
    assert not EntityResolver().resolve_many("Compras por cliente por shopping").matches


def test_shopping_nicknames_are_available_in_knowledge_context():
    rules = KnowledgeService().get_context().rules
    description = next(rule.description for rule in rules if rule.code == "shopping_nicknames")
    for nickname, name in SHOPPING_NICKNAMES:
        assert nickname in description
        assert name in description


@pytest.mark.parametrize("nickname,name", SHOPPING_NICKNAMES)
@pytest.mark.parametrize("template", [
    "Qual a frequência de compras por cliente no {nickname}?",
    "Liste as campanhas do {nickname}",
])
def test_shopping_nickname_filters_only_the_requested_shopping(nickname, name, template):
    import pandas as pd
    from test_business_analysis_flow import business_frame
    from test_recent_campaign import service

    frame = business_frame().iloc[:2].copy()
    frame["nm_empreendimento"] = name
    other = frame.copy()
    other["nm_empreendimento"] = "Shopping sem apelido"
    other["cd_compra"] += "-other"
    other["nm_promocao"] = "Campanha de outro shopping"
    response = service(frame=pd.concat([frame, other], ignore_index=True)).execute_question(
        question=template.format(nickname=nickname),
        knowledge_context=KnowledgeService().get_context(),
    )
    assert response.data, response.answer
    if "frequência" in template:
        assert len(response.data) == 1
        assert response.data[0]["quantidade_compras"] == 2
        assert response.data[0]["frequencia_media"] == 1
    else:
        assert {row["nm_empreendimento"] for row in response.data} == {name}
    assert "Campanha de outro shopping" not in response.answer


@pytest.mark.parametrize(
    ("mention", "field", "value"),
    [
        ("arcaparque", "nm_promocao", "Promoção Verão no Arca Parque 2026"),
        ("camarada", "nm_fantasa", "Camarada Camarão"),
        ("c&a", "nm_fantasa", "C&A"),
        ("boticario", "nm_fantasa", "O Boticário"),
        ("casas bahia", "nm_fantasa", "Casas Bahia"),
    ],
)
def test_entity_resolver_resolves_registered_entities(
    mention: str,
    field: str,
    value: str,
) -> None:
    result = EntityResolver().resolve(f"Qual foi o faturamento de {mention}?")

    assert result.is_ambiguous is False
    assert len(result.matches) == 1
    assert result.matches[0].field == field
    assert result.matches[0].value == value
    assert result.matches[0].confidence >= 0.78


def test_entity_resolution_adds_full_value_filter_to_execution_plan() -> None:
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        entity_resolver=EntityResolver(),
    )
    question = "Qual foi o faturamento do arcaparque?"
    semantic_resolution = SemanticResolver().resolve(question)

    response = compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=KnowledgeService().get_context(),
        ),
    )

    assert response.hypothesis.business_entity == "promocao"
    assert any(
        operation.type == "filter"
        and operation.field == "nm_promocao"
        and operation.parameters["operator"] == "equals"
        and operation.parameters["value"] == "Promoção Verão no Arca Parque 2026"
        for operation in response.execution_plan.operations
    )
def test_generic_shopping_question_does_not_create_named_entity_filters() -> None:
    result = EntityResolver().resolve_many(
        "Qual foi a campanha de maior faturamento e em que shopping ocorreu?"
    )

    assert result.matches == []


def test_specific_shopping_name_wins_over_overlapping_generic_candidate() -> None:
    compiler = TerbieCompiler(
        hypothesis_builder=HypothesisBuilder(),
        analytical_planner=AnalyticalPlanner(),
        execution_plan_builder=ExecutionPlanBuilder(),
        validator=PlanValidator(),
        optimizer=PlanOptimizer(),
        entity_resolver=EntityResolver(),
    )
    question = "Liste as campanhas que ocorreram no Buriti Shopping Rio Verde"

    response = compiler.compile(
        CompilerRequest(
            question=question,
            semantic_resolution=SemanticResolver().resolve(question),
            knowledge_context=KnowledgeService().get_context(),
        ),
    )

    entity_filters = [
        operation
        for operation in response.execution_plan.operations
        if operation.type == "filter"
        and operation.field == "nm_empreendimento"
        and operation.parameters.get("operator") == "equals"
    ]
    assert len(entity_filters) == 1
    assert entity_filters[0].field == "nm_empreendimento"
    assert entity_filters[0].parameters["value"] == "Buriti Shopping Rio Verde"
