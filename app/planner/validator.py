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
        "campaign_detail",
        "derive_demographics",
        "persona_profile",
        "persona_comparison",
        "campaign_context_comparison",
        "filter_group",
        "statistics",
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

        warnings.extend(self._operation_order_warnings(plan))
        warnings.extend(self._context_comparison_warnings(plan))

        return PlanValidationResult(is_valid=not warnings, warnings=warnings)

    def _context_comparison_warnings(self, plan: ExecutionPlan) -> list[str]:
        warnings: list[str] = []
        for operation in plan.operations:
            if operation.type != "campaign_context_comparison":
                continue
            contexts = operation.parameters.get("contexts", [])
            if not isinstance(contexts, list) or len(contexts) < 2:
                warnings.append("A comparação contextual exige pelo menos dois itens.")
                continue
            keys: list[tuple[str, str]] = []
            for context in contexts:
                if not isinstance(context, dict) or not context.get("promotion") or not context.get("shopping"):
                    warnings.append("Campanha e shopping são obrigatórios em cada item comparado.")
                    continue
                keys.append((str(context["promotion"]).casefold(), str(context["shopping"]).casefold()))
            if len(keys) != len(set(keys)):
                warnings.append("A comparação contém itens duplicados.")
        return warnings

    def _operation_order_warnings(self, plan: ExecutionPlan) -> list[str]:
        warnings: list[str] = []
        operation_types = [operation.type for operation in plan.operations]
        aggregate_positions = [
            index
            for index, operation_type in enumerate(operation_types)
            if operation_type in {"aggregate", "statistics"}
        ]
        if aggregate_positions:
            first_aggregate = min(aggregate_positions)
            if any(
                operation_type in {"filter", "filter_group"}
                for operation_type in operation_types[first_aggregate + 1 :]
            ):
                warnings.append("Filtros devem ser executados antes das agregações.")

        if (
            "limit" in operation_types
            and "sort" in operation_types
            and operation_types.index("limit") < operation_types.index("sort")
        ):
            warnings.append("Ordenação deve ocorrer antes do limite em rankings.")

        return warnings
