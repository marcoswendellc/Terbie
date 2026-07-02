from typing import Any

from app.planner.models import ExecutionPlan


class PlanParser:
    """Parses a raw mapping into an ExecutionPlan using Pydantic validation."""

    def parse(self, payload: dict[str, Any]) -> ExecutionPlan:
        return ExecutionPlan.model_validate(payload)
