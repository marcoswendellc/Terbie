from app.planner.models import ExecutionPlan


class PlanOptimizer:
    """Applies safe, semantics-preserving optimizations to an execution plan."""

    def optimize(self, plan: ExecutionPlan) -> ExecutionPlan:
        operations = []
        seen_filters: set[str] = set()
        for operation in plan.operations:
            if operation.type in {"filter", "filter_group"}:
                signature = operation.model_dump_json()
                if signature in seen_filters:
                    continue
                seen_filters.add(signature)
            operations.append(operation)

        return plan.model_copy(update={"operations": operations})
