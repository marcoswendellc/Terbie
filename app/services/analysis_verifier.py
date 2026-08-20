from dataclasses import dataclass, field

from app.executor.models import ExecutionResult
from app.planner.models import ExecutionPlan


@dataclass(frozen=True, slots=True)
class VerificationResult:
    passed: bool
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)


class AnalysisVerifier:
    """Checks calculated results before they are narrated to the user."""

    def verify(self, *, plan: ExecutionPlan, result: ExecutionResult) -> VerificationResult:
        warnings: list[str] = []
        checks = {
            "has_rows": result.rows_returned > 0,
            "filters_preserved": self._filters_preserved(plan, result),
            "percentages_valid": self._percentages_valid(result),
            "dominant_values_valid": self._dominant_values_valid(result),
        }
        if not checks["has_rows"]:
            # Empty results are valid business outcomes; the narrator handles them safely.
            pass
        if not checks["filters_preserved"]:
            warnings.append("Nem todos os filtros planejados foram rastreados na execução.")
        if not checks["percentages_valid"]:
            warnings.append("O resultado contém percentual fora do intervalo de 0% a 100%.")
        if not checks["dominant_values_valid"]:
            warnings.append("O perfil predominante contém valor nulo ou não informado.")
        return VerificationResult(passed=all(checks.values()), warnings=warnings, checks=checks)

    def _filters_preserved(self, plan: ExecutionPlan, result: ExecutionResult) -> bool:
        planned = sum(
            operation.type in {"filter", "filter_group"} for operation in plan.operations
        )
        traced = sum(
            item.get("operation") in {"filter", "filter_group"}
            for item in result.metadata.get("operation_trace", [])
            if isinstance(item, dict)
        )
        return traced >= planned

    def _percentages_valid(self, result: ExecutionResult) -> bool:
        return all(
            0 <= float(value) <= 1
            for row in result.data
            for key, value in row.items()
            if key.startswith("percentual_") or key == "participacao"
            if isinstance(value, int | float)
        )

    def _dominant_values_valid(self, result: ExecutionResult) -> bool:
        invalid = {None, "", "NULL", "None", "nan", "Não informado"}
        return all(
            value not in invalid
            for row in result.data
            for key, value in row.items()
            if key.endswith("_predominante")
        )
