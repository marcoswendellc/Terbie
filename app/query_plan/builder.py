from typing import Any

from app.planner.models import ExecutionPlan, PlanOperation
from app.query_plan.models import LogicalPlanNode, LogicalQueryPlan


class LogicalQueryPlanBuilder:
    """Builds a logical query plan from the current ExecutionPlan DSL."""

    def build(
        self,
        execution_plan: ExecutionPlan,
        *,
        source: str | None = None,
        table: str | None = None,
    ) -> LogicalQueryPlan:
        nodes: list[LogicalPlanNode] = [
            LogicalPlanNode(
                id="scan_1",
                type="scan",
                inputs=[],
                parameters={
                    "intent": execution_plan.intent,
                    "entities": [
                        entity.model_dump(mode="json") for entity in execution_plan.entities
                    ],
                    "metrics": [
                        metric.model_dump(mode="json") for metric in execution_plan.metrics
                    ],
                    "plan_parameters": [
                        parameter.model_dump(mode="json")
                        for parameter in execution_plan.parameters
                    ],
                    "is_executable": execution_plan.is_executable,
                },
            ),
        ]

        previous_node_id = "scan_1"
        operation_counts: dict[str, int] = {}
        for operation in execution_plan.operations:
            operation_counts[operation.type] = operation_counts.get(operation.type, 0) + 1
            node_id = f"{operation.type}_{operation_counts[operation.type]}"
            nodes.append(
                LogicalPlanNode(
                    id=node_id,
                    type=operation.type,
                    inputs=[previous_node_id],
                    parameters=self._operation_parameters(operation),
                ),
            )
            previous_node_id = node_id

        return LogicalQueryPlan(
            source=source,
            table=table,
            nodes=nodes,
            warnings=execution_plan.warnings,
            is_valid=False,
        )

    def _operation_parameters(self, operation: PlanOperation) -> dict[str, Any]:
        payload = operation.model_dump(mode="json")
        return {key: value for key, value in payload.items() if value not in (None, {})}
