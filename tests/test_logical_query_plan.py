from fastapi.testclient import TestClient

from app.main import app
from app.planner.models import (
    ExecutionPlan,
    PlanEntity,
    PlanMetric,
    PlanOperation,
    PlanParameter,
)
from app.query_plan.adapter import LogicalQueryPlanAdapter
from app.query_plan.builder import LogicalQueryPlanBuilder
from app.query_plan.models import LogicalPlanNode, LogicalQueryPlan
from app.query_plan.validator import LogicalQueryPlanValidator


def _execution_plan() -> ExecutionPlan:
    return ExecutionPlan(
        intent="ranking",
        entities=[PlanEntity(name="restaurante")],
        metrics=[PlanMetric(name="faturamento", aggregation="sum")],
        parameters=[PlanParameter(type="limit", value=10)],
        operations=[
            PlanOperation(type="group_by", field="restaurante"),
            PlanOperation(type="aggregate", function="sum", alias="faturamento"),
            PlanOperation(
                type="sort",
                field="faturamento",
                parameters={"direction": "desc"},
            ),
            PlanOperation(type="limit", parameters={"value": 10}),
        ],
        warnings=[],
        is_executable=False,
    )


def test_logical_query_plan_builder_creates_scan_node() -> None:
    logical_plan = LogicalQueryPlanBuilder().build(_execution_plan())

    assert logical_plan.nodes[0].id == "scan_1"
    assert logical_plan.nodes[0].type == "scan"
    assert logical_plan.nodes[0].inputs == []


def test_logical_query_plan_builder_converts_aggregate_sort_and_limit() -> None:
    logical_plan = LogicalQueryPlanBuilder().build(_execution_plan())
    node_types = [node.type for node in logical_plan.nodes]

    assert "aggregate" in node_types
    assert "sort" in node_types
    assert "limit" in node_types
    assert logical_plan.nodes[-1].type == "limit"
    assert logical_plan.nodes[-1].parameters["parameters"] == {"value": 10}


def test_logical_query_plan_validator_accepts_valid_plan() -> None:
    logical_plan = LogicalQueryPlanBuilder().build(_execution_plan())

    validation = LogicalQueryPlanValidator().validate(logical_plan)

    assert validation.is_valid is True
    assert validation.errors == []


def test_logical_query_plan_validator_rejects_missing_input() -> None:
    logical_plan = LogicalQueryPlan(
        nodes=[
            LogicalPlanNode(id="scan_1", type="scan"),
            LogicalPlanNode(id="limit_1", type="limit", inputs=["missing_node"]),
        ],
    )

    validation = LogicalQueryPlanValidator().validate(logical_plan)

    assert validation.is_valid is False
    assert "missing_node" in validation.errors[0]


def test_logical_query_plan_adapter_converts_lqp_to_execution_plan() -> None:
    logical_plan = LogicalQueryPlanBuilder().build(_execution_plan())

    execution_plan = LogicalQueryPlanAdapter().to_execution_plan(logical_plan)

    assert execution_plan.intent == "ranking"
    assert execution_plan.entities[0].name == "restaurante"
    assert execution_plan.metrics[0].name == "faturamento"
    assert [operation.type for operation in execution_plan.operations] == [
        "group_by",
        "aggregate",
        "sort",
        "limit",
    ]


def test_query_plan_draft_endpoint_returns_200() -> None:
    client = TestClient(app)

    response = client.post(
        "/query-plan/draft",
        json={"question": "Quais são os 10 restaurantes com maior faturamento?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "Quais são os 10 restaurantes com maior faturamento?"
    assert payload["validation"]["is_valid"] is True
    assert payload["logical_query_plan"]["nodes"][0]["type"] == "scan"
