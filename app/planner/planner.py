from app.planner.models import (
    ExecutionPlan,
    PlanEntity,
    PlanMetric,
    PlanOperation,
    PlanParameter,
)
from app.semantic.models import SemanticResolution


class QueryPlanner:
    """Deterministic draft planner for the first declarative Terbie DSL."""

    _METRIC_AGGREGATIONS: dict[str, str] = {
        "faturamento": "sum",
        "ticket_medio": "avg",
    }
    _SUPPORTED_ENTITIES = {"restaurante", "loja"}

    def create_plan(
        self,
        *,
        question: str,
        semantic_resolution: SemanticResolution,
    ) -> ExecutionPlan:
        _ = question
        intent = self._intent(semantic_resolution)
        entities = self._entities(semantic_resolution)
        metrics = self._metrics(semantic_resolution)
        parameters = self._parameters(semantic_resolution)
        operations = self._operations(
            intent=intent,
            metrics=metrics,
            parameters=parameters,
        )

        return ExecutionPlan(
            intent=intent,
            entities=entities,
            metrics=metrics,
            parameters=parameters,
            operations=operations,
            warnings=semantic_resolution.warnings,
            is_executable=False,
        )

    def _intent(self, semantic_resolution: SemanticResolution) -> str | None:
        if any(term.canonical == "ranking" for term in semantic_resolution.matched_terms):
            return "ranking"

        return None

    def _entities(self, semantic_resolution: SemanticResolution) -> list[PlanEntity]:
        entities: list[PlanEntity] = []
        seen: set[str] = set()

        for entity in semantic_resolution.suggested_entities:
            if entity.name not in self._SUPPORTED_ENTITIES or entity.name in seen:
                continue

            entities.append(PlanEntity(name=entity.name))
            seen.add(entity.name)

        return entities

    def _metrics(self, semantic_resolution: SemanticResolution) -> list[PlanMetric]:
        metrics: list[PlanMetric] = []
        seen: set[str] = set()

        for metric in semantic_resolution.suggested_metrics:
            aggregation = self._METRIC_AGGREGATIONS.get(metric.name)
            if aggregation is None or metric.name in seen:
                continue

            metrics.append(PlanMetric(name=metric.name, aggregation=aggregation))
            seen.add(metric.name)

        return metrics

    def _parameters(self, semantic_resolution: SemanticResolution) -> list[PlanParameter]:
        return [
            PlanParameter(type=parameter.type, value=parameter.value)
            for parameter in semantic_resolution.parameters
            if parameter.type in {"limit", "period"}
        ]

    def _operations(
        self,
        *,
        intent: str | None,
        metrics: list[PlanMetric],
        parameters: list[PlanParameter],
    ) -> list[PlanOperation]:
        operations: list[PlanOperation] = []

        for metric in metrics:
            operations.append(
                PlanOperation(
                    type="aggregate",
                    function=metric.aggregation,
                    alias=metric.name,
                ),
            )

        if intent == "ranking":
            sort_field = metrics[0].name if metrics else None
            operations.append(
                PlanOperation(
                    type="sort",
                    field=sort_field,
                    parameters={"direction": "desc"},
                ),
            )

        for parameter in parameters:
            if parameter.type == "limit":
                operations.append(
                    PlanOperation(
                        type="limit",
                        parameters={"value": parameter.value},
                    ),
                )

        return operations
