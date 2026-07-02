from app.query_plan.models import LogicalPlanValidationResult, LogicalQueryPlan


class LogicalQueryPlanValidator:
    """Validates structural correctness of a Logical Query Plan."""

    _SUPPORTED_NODE_TYPES = {"scan", "filter", "group_by", "aggregate", "sort", "limit"}

    def validate(self, plan: LogicalQueryPlan) -> LogicalPlanValidationResult:
        warnings = list(plan.warnings)
        errors: list[str] = []
        node_ids = [node.id for node in plan.nodes]
        node_id_set = set(node_ids)

        if not any(node.type == "scan" for node in plan.nodes):
            errors.append("LogicalQueryPlan must include a scan node.")

        if len(node_ids) != len(node_id_set):
            errors.append("LogicalQueryPlan node ids must be unique.")

        for node in plan.nodes:
            if node.type not in self._SUPPORTED_NODE_TYPES:
                errors.append(f"Unsupported logical plan node type: {node.type}.")

            for input_id in node.inputs:
                if input_id not in node_id_set:
                    errors.append(
                        f"Node '{node.id}' references missing input node '{input_id}'.",
                    )

        return LogicalPlanValidationResult(
            is_valid=not errors,
            warnings=warnings,
            errors=errors,
        )
