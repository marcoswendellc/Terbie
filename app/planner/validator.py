from app.planner.models import ExecutionPlan, PlanValidationResult


class PlanValidator:
    """Validates draft plan structure without raising for incomplete plans."""

    _KNOWN_OPERATIONS = {
        "select",
        "distinct",
        "derived_metric",
        "filter",
        "group_by",
        "aggregate",
        "sort",
        "limit",
        "compare_periods",
        "growth",
        "rank",
        "share",
        "trend",
        "outlier",
    }

    def validate(self, plan: ExecutionPlan) -> PlanValidationResult:
        warnings: list[str] = []

        if not plan.version:
            warnings.append("Plano sem versão.")

        if not plan.metrics and not plan.entities:
            warnings.append("Plano sem métricas ou entidades.")

        for operation in plan.operations:
            if operation.type not in self._KNOWN_OPERATIONS:
                warnings.append(f"Operação desconhecida: {operation.type}.")

        return PlanValidationResult(is_valid=not warnings, warnings=warnings)
