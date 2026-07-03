from app.compiler.models import AnalyticalPlan
from app.planner.models import (
    ExecutionPlan,
    PlanEntity,
    PlanMetric,
    PlanOperation,
    PlanParameter,
)


class ExecutionPlanBuilder:
    """Converts an analytical plan into the current Terbie ExecutionPlan DSL."""

    _METRIC_AGGREGATIONS = {
        "faturamento": "sum",
        "ticket_medio": "avg",
        "quantidade_compras": "count_distinct",
        "clientes_unicos": "count_distinct",
    }

    def build(self, analytical_plan: AnalyticalPlan) -> ExecutionPlan:
        metrics = [
            PlanMetric(name=metric, aggregation=self._METRIC_AGGREGATIONS.get(metric))
            for metric in analytical_plan.metrics
        ]
        entities = [PlanEntity(name=entity) for entity in analytical_plan.entities]
        parameters = self._parameters(analytical_plan)

        return ExecutionPlan(
            intent=analytical_plan.intent,
            entities=entities,
            metrics=metrics,
            parameters=parameters,
            operations=self._operations(
                analytical_plan=analytical_plan,
                metrics=metrics,
                parameters=parameters,
            ),
            warnings=analytical_plan.warnings,
            is_executable=False,
        )

    def _parameters(self, analytical_plan: AnalyticalPlan) -> list[PlanParameter]:
        parameters: list[PlanParameter] = []

        if analytical_plan.time_scope is not None:
            parameters.append(PlanParameter(type="period", value=analytical_plan.time_scope))

        for filter_item in analytical_plan.filters:
            parameter_type = filter_item.get("type", "filter")
            parameter_value = filter_item.get("value", filter_item)
            if any(
                parameter.type == parameter_type and parameter.value == parameter_value
                for parameter in parameters
            ):
                continue

            parameters.append(PlanParameter(type=parameter_type, value=parameter_value))

        return parameters

    def _operations(
        self,
        *,
        analytical_plan: AnalyticalPlan,
        metrics: list[PlanMetric],
        parameters: list[PlanParameter],
    ) -> list[PlanOperation]:
        operations: list[PlanOperation] = []
        metric = metrics[0] if metrics else None
        limit_parameter = self._limit_parameter(parameters)
        group_field = analytical_plan.dimensions[0] if analytical_plan.dimensions else (
            analytical_plan.entities[0] if analytical_plan.entities else None
        )
        select_fields = self._select_fields(analytical_plan)
        distinct_fields = self._distinct_fields(analytical_plan)

        operations.extend(self._filter_operations(analytical_plan.filters))

        for operation_name in analytical_plan.required_operations:
            if operation_name == "filter":
                continue

            operation = self._operation(
                operation_name=operation_name,
                metric=metric,
                group_field=group_field,
                limit_parameter=limit_parameter,
                select_fields=select_fields,
                distinct_fields=distinct_fields,
                intent=analytical_plan.intent,
            )
            if operation is not None:
                operations.append(operation)

        return operations

    def _filter_operations(self, filters: list[dict[str, object]]) -> list[PlanOperation]:
        operations: list[PlanOperation] = []

        for filter_item in filters:
            if filter_item.get("type") != "filter":
                continue

            field = filter_item.get("field")
            if not isinstance(field, str):
                continue

            parameters = {
                "operator": filter_item.get("operator", "equals"),
                "value": filter_item.get("value"),
            }
            end_field = filter_item.get("end_field")
            if end_field is not None:
                parameters["end_field"] = end_field

            operations.append(
                PlanOperation(
                    type="filter",
                    field=field,
                    parameters=parameters,
                ),
            )

        return operations

    def _operation(
        self,
        *,
        operation_name: str,
        metric: PlanMetric | None,
        group_field: str | None,
        limit_parameter: PlanParameter | None,
        select_fields: list[str],
        distinct_fields: list[str],
        intent: str | None,
    ) -> PlanOperation | None:
        if operation_name == "select":
            return PlanOperation(type="select", parameters={"fields": select_fields})

        if operation_name == "distinct":
            return PlanOperation(type="distinct", parameters={"subset": distinct_fields})

        if operation_name == "group_by":
            return PlanOperation(type="group_by", field=group_field)

        if operation_name == "aggregate":
            if intent == "comparison":
                return PlanOperation(
                    type="aggregate",
                    parameters={
                        "metrics": [
                            {
                                "name": "faturamento",
                                "field": "vl_compra",
                                "function": "sum",
                                "alias": "faturamento",
                            },
                            {
                                "name": "quantidade_compras",
                                "field": "cd_compra",
                                "function": "count_distinct",
                                "alias": "quantidade_compras",
                            },
                            {
                                "name": "clientes_unicos",
                                "field": "sk_cliente",
                                "function": "count_distinct",
                                "alias": "clientes_unicos",
                            },
                        ],
                    },
                )

            return PlanOperation(
                type="aggregate",
                function=metric.aggregation if metric is not None else None,
                alias=metric.name if metric is not None else None,
            )

        if operation_name == "derived_metric":
            return PlanOperation(
                type="derived_metric",
                alias="ticket_medio",
                parameters={
                    "numerator": "faturamento",
                    "denominator": "quantidade_compras",
                },
            )

        if operation_name == "sort":
            if intent == "comparison":
                return PlanOperation(
                    type="sort",
                    field="faturamento",
                    parameters={"direction": "desc"},
                )

            if select_fields:
                sort_field = "sk_dtinicio" if "sk_dtinicio" in select_fields else select_fields[0]
                return PlanOperation(
                    type="sort",
                    field=sort_field,
                    parameters={"direction": "asc"},
                )

            return PlanOperation(
                type="sort",
                field=metric.name if metric is not None else None,
                parameters={"direction": "desc"},
            )

        if operation_name == "limit":
            limit_value = limit_parameter.value if limit_parameter is not None else None
            return PlanOperation(type="limit", parameters={"value": limit_value})

        return PlanOperation(type=operation_name)

    def _limit_parameter(self, parameters: list[PlanParameter]) -> PlanParameter | None:
        for parameter in parameters:
            if parameter.type == "limit":
                return parameter

        return None

    def _select_fields(self, analytical_plan: AnalyticalPlan) -> list[str]:
        if analytical_plan.intent == "list_distinct" and "promocao" in analytical_plan.entities:
            return ["cd_promocao", "nm_promocao", "sk_dtinicio", "sk_dtfim"]

        return []

    def _distinct_fields(self, analytical_plan: AnalyticalPlan) -> list[str]:
        if analytical_plan.intent == "list_distinct" and "promocao" in analytical_plan.entities:
            return ["cd_promocao", "nm_promocao"]

        return []
