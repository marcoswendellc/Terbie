from collections.abc import Callable
from dataclasses import dataclass, field

from app.executor.models import ExecutionResult
from app.planner.models import ExecutionPlan
from app.services.analysis_verifier import AnalysisVerifier, VerificationResult


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    plan: ExecutionPlan
    result: ExecutionResult
    verification: VerificationResult
    attempts: int
    audit: list[dict[str, object]] = field(default_factory=list)


class AnalyticalAgent:
    """Bounded plan-execute-verify-repair loop; never repairs more than configured."""

    def __init__(self, verifier: AnalysisVerifier | None = None, *, max_repairs: int = 1) -> None:
        self._verifier = verifier or AnalysisVerifier()
        self._max_repairs = max(max_repairs, 0)

    def run(
        self,
        *,
        plan: ExecutionPlan,
        execute: Callable[[ExecutionPlan], ExecutionResult],
        repair: Callable[[ExecutionPlan, VerificationResult], ExecutionPlan | None],
    ) -> AgentRunResult:
        current_plan = plan
        audit: list[dict[str, object]] = []
        for attempt in range(1, self._max_repairs + 2):
            result = execute(current_plan)
            verification = self._verifier.verify(plan=current_plan, result=result)
            audit.append(
                {
                    "attempt": attempt,
                    "passed": verification.passed,
                    "checks": verification.checks,
                },
            )
            if verification.passed or attempt > self._max_repairs:
                return AgentRunResult(
                    plan=current_plan,
                    result=result,
                    verification=verification,
                    attempts=attempt,
                    audit=audit,
                )
            repaired = repair(current_plan, verification)
            if repaired is None or repaired == current_plan:
                return AgentRunResult(
                    plan=current_plan,
                    result=result,
                    verification=verification,
                    attempts=attempt,
                    audit=audit,
                )
            current_plan = repaired

        raise RuntimeError("Unreachable analytical agent state")
