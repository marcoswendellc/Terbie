from typing import Any

from app.planner.models import (
    ExecutionPlan,
    PlanEntity,
    PlanMetric,
    PlanOperation,
    PlanParameter,
)
from app.query_plan.models import LogicalQueryPlan


class LogicalQueryPlanAdapter:
    """Converts LogicalQueryPlan back to the current ExecutionPlan DSL."""

    _OPERATION_NODE_TYPES = {"filter", "group_by", "aggregate", "sort", "limit"}

    def to_execution_plan(self, logical_plan: LogicalQueryPlan) -> ExecutionPlan:
        scan_parameters = self._scan_parameters(logical_plan)
        return ExecutionPlan(
            version=logical_plan.version,
            intent=scan_parameters.get("intent"),
            entities=[
                PlanEntity(**entity)
                for entity in scan_parameters.get("entities", [])
                if isinstance(entity, dict)
            ],
            metrics=[
                PlanMetric(**metric)
                for metric in scan_parameters.get("metrics", [])
                if isinstance(metric, dict)
            ],
            parameters=[
                PlanParameter(**parameter)
                for parameter in scan_parameters.get("plan_parameters", [])
                if isinstance(parameter, dict)
            ],
            operations=[
                self._to_plan_operation(node.parameters)
                for node in logical_plan.nodes
                if node.type in self._OPERATION_NODE_TYPES
            ],
            warnings=logical_plan.warnings,
            is_executable=bool(scan_parameters.get("is_executable", False)),
        )

    def _scan_parameters(self, logical_plan: LogicalQueryPlan) -> dict[str, Any]:
        for node in logical_plan.nodes:
            if node.type == "scan":
                return node.parameters
        return {}

    def _to_plan_operation(self, parameters: dict[str, Any]) -> PlanOperation:
        return PlanOperation(
            type=str(parameters.get("type")),
            function=parameters.get("function"),
            field=parameters.get("field"),
            alias=parameters.get("alias"),
            parameters=parameters.get("parameters", {}),
        )
