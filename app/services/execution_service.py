import logging
import re
import unicodedata

import pandas as pd

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, DataSourceError
from app.executor.executor import TerbieExecutor
from app.insights.generator import InsightGenerator
from app.intent_guard.intent_guard import IntentGuard
from app.knowledge.models import KnowledgeContext
from app.narrator.models import ExecuteResponse, NarratorRequest
from app.planner.models import ExecutionPlan
from app.query_plan.models import MultiQueryPlan, QueryPlan
from app.query_plan.multi import MultiQueryPlanner
from app.services.data_service import DataService
from app.services.narrator_service import NarratorService
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService

logger = logging.getLogger(__name__)


class ExecutionService:
    """Coordinates semantic resolution, planning, data loading, and execution."""

    _SENSITIVE_COLUMNS = {"senha", "password", "token", "secret"}
    _REQUIRED_COLUMNS_CAMPAIGN_DETAIL = {"nm_promocao", "vl_compra"}

    def __init__(
        self,
        settings: Settings,
        semantic_service: SemanticService,
        planner_service: PlannerService,
        data_service: DataService,
        executor: TerbieExecutor,
        narrator_service: NarratorService,
        intent_guard: IntentGuard | None = None,
        insight_generator: InsightGenerator | None = None,
    ) -> None:
        self._settings = settings
        self._semantic_service = semantic_service
        self._planner_service = planner_service
        self._data_service = data_service
        self._executor = executor
        self._narrator_service = narrator_service
        self._intent_guard = intent_guard or IntentGuard()
        self._insight_generator = insight_generator or InsightGenerator()

    def execute_question(
        self,
        *,
        question: str,
        knowledge_context: KnowledgeContext,
    ) -> ExecuteResponse:
        intent_guard_result = self._intent_guard.evaluate(question)
        if intent_guard_result.should_stop:
            return self._routed_response(
                question,
                response=intent_guard_result.response or "",
                response_type=intent_guard_result.intent,
            )

        multi_query_plan = MultiQueryPlanner(
            semantic_service=self._semantic_service,
            planner_service=self._planner_service,
        ).build(question=question, knowledge_context=knowledge_context)
        if multi_query_plan is not None:
            return self._execute_multi_query(
                multi_query_plan=multi_query_plan,
                knowledge_context=knowledge_context,
            )

        semantic_resolution = self._semantic_service.resolve(question=question)
        planner_response = self._planner_service.create_draft_plan(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=knowledge_context,
        )
        dataframes = self._load_dataframes()
        dataframe = self._select_dataframe(
            dataframes=dataframes,
            plan=planner_response.plan,
            knowledge_context=knowledge_context,
        )
        result = self._executor.execute(
            dataframe=dataframe,
            plan=planner_response.plan,
            knowledge_context=knowledge_context,
        )
        ranking_metadata = self._ranking_metadata(
            semantic_resolution=semantic_resolution,
            plan=planner_response.plan,
            execution_metadata=result.metadata,
        )
        self._log_composite_filter_validation(
            question=question,
            plan=planner_response.plan,
            result=result,
        )
        enriched_result = result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "question": question,
                    "selected_table": dataframe.attrs.get("table_name"),
                    **({"ranking": ranking_metadata} if ranking_metadata else {}),
                },
            },
        )
        insight_result = self._insight_generator.generate(
            enriched_result,
            analytical_plan=None,
            execution_plan=planner_response.plan,
        )
        if (
            not insight_result.summary
            and not insight_result.insights
            and not insight_result.recommendations
        ):
            insight_result = None
        narrator_response = self._narrator_service.narrate(
            NarratorRequest(
                question=question,
                execution_result=enriched_result,
                semantic_resolution=semantic_resolution,
                execution_plan=planner_response.plan,
                insight_result=insight_result,
            ),
        )

        return ExecuteResponse(
            question=question,
            answer=narrator_response.answer,
            highlights=[],
            insights=[],
            recommendations=[],
            data=self._sanitize_rows(enriched_result.data),
            metadata={**enriched_result.metadata, **narrator_response.metadata},
            warnings=list(
                dict.fromkeys([*enriched_result.warnings, *narrator_response.warnings]),
            ),
        )

    def _execute_multi_query(
        self,
        *,
        multi_query_plan: MultiQueryPlan,
        knowledge_context: KnowledgeContext,
    ) -> ExecuteResponse:
        result_items: list[dict[str, object]] = []
        answer_sections: list[str] = []
        warnings: list[str] = []

        for query_plan in multi_query_plan.plans:
            try:
                response = self._execute_compiled_query(
                    query_plan=query_plan,
                    knowledge_context=knowledge_context,
                )
            except Exception:  # Each independent plan is a partial-failure boundary.
                message = f"{query_plan.title}: não foi possível responder esta parte."
                logger.exception("MultiQueryPlan item failed: %s", query_plan.id)
                warnings.append(message)
                result_items.append(
                    {
                        "id": query_plan.id,
                        "title": query_plan.title,
                        "status": "failed",
                        "data": [],
                        "filters": query_plan.filters,
                    },
                )
                answer_sections.append(f"{query_plan.title}\n{message}")
                continue

            filters = self._visible_filters(query_plan)
            result_items.append(
                {
                    "id": query_plan.id,
                    "title": query_plan.title,
                    "status": "success",
                    "data": response.data,
                    "filters": query_plan.filters,
                    "warnings": response.warnings,
                },
            )
            section = f"{query_plan.title}\n{response.answer}"
            if filters:
                section += f"\nFiltros considerados: {filters}."
            answer_sections.append(section)
            warnings.extend(response.warnings)

        return ExecuteResponse(
            question=multi_query_plan.question,
            answer="\n\n".join(answer_sections),
            data=result_items,
            metadata={
                "response_type": "multi_query",
                "multi_query_plan": multi_query_plan.model_dump(mode="json"),
                "successful_plans": sum(
                    item["status"] == "success" for item in result_items
                ),
                "failed_plans": sum(item["status"] == "failed" for item in result_items),
            },
            warnings=warnings,
        )

    def _execute_compiled_query(
        self,
        *,
        query_plan: QueryPlan,
        knowledge_context: KnowledgeContext,
    ) -> ExecuteResponse:
        semantic_resolution = self._semantic_service.resolve(question=query_plan.question)
        plan = query_plan.execution_plan
        dataframes = self._load_dataframes()
        dataframe = self._select_dataframe(
            dataframes=dataframes,
            plan=plan,
            knowledge_context=knowledge_context,
        )
        result = self._executor.execute(
            dataframe=dataframe,
            plan=plan,
            knowledge_context=knowledge_context,
        )
        enriched_result = result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "question": query_plan.question,
                    "selected_table": dataframe.attrs.get("table_name"),
                    "query_plan_id": query_plan.id,
                    "query_plan_title": query_plan.title,
                },
            },
        )
        narrator_response = self._narrator_service.narrate(
            NarratorRequest(
                question=query_plan.question,
                execution_result=enriched_result,
                semantic_resolution=semantic_resolution,
                execution_plan=plan,
            ),
        )
        return ExecuteResponse(
            question=query_plan.question,
            answer=narrator_response.answer,
            data=self._sanitize_rows(enriched_result.data),
            metadata={**enriched_result.metadata, **narrator_response.metadata},
            warnings=list(
                dict.fromkeys([*enriched_result.warnings, *narrator_response.warnings]),
            ),
        )

    def _visible_filters(self, query_plan: QueryPlan) -> str:
        labels = {
            "nm_promocao": "campanha",
            "nm_segmento": "segmento",
            "nm_fantasa": "loja",
            "nm_empreendimento": "shopping",
        }
        parts = [
            f"{labels.get(str(item.get('field')), item.get('field'))} = {item.get('value')}"
            for item in query_plan.filters
            if item.get("operator") == "equals" and item.get("value") is not None
        ]
        return ", ".join(parts)

    def _ranking_metadata(
        self,
        *,
        semantic_resolution: object,
        plan: ExecutionPlan,
        execution_metadata: dict[str, object],
    ) -> dict[str, object]:
        if plan.intent != "ranking":
            return {}

        requested_limit = next(
            (
                parameter.value
                for parameter in getattr(semantic_resolution, "parameters", [])
                if parameter.type == "limit" and isinstance(parameter.value, int)
            ),
            None,
        )
        planned_limit = next(
            (
                operation.parameters.get("value")
                for operation in plan.operations
                if operation.type == "limit"
            ),
            None,
        )
        return {
            "requested_limit": requested_limit,
            "planned_limit": planned_limit,
            "executed_limit": execution_metadata.get("executed_limit"),
            "order": execution_metadata.get("order"),
            "order_by": execution_metadata.get("order_by"),
        }

    def _load_dataframes(self) -> dict[str, pd.DataFrame]:
        spreadsheet_id = self._settings.google_sheets_spreadsheet_id
        if spreadsheet_id is None or spreadsheet_id.strip() == "":
            raise ConfigurationError(
                "Google Sheets spreadsheet ID is not configured",
                details={"expected": "GOOGLE_SHEETS_SPREADSHEET_ID"},
            )

        return self._data_service.read_google_spreadsheet_data(
            spreadsheet_id=spreadsheet_id,
            sheet_names=[self._settings.default_table],
        )

    def _select_dataframe(
        self,
        *,
        dataframes: dict[str, pd.DataFrame],
        plan: ExecutionPlan,
        knowledge_context: KnowledgeContext,
    ) -> pd.DataFrame:
        required_columns = self._required_columns(plan=plan, knowledge_context=knowledge_context)
        for table_name, dataframe in dataframes.items():
            if table_name != self._settings.default_table:
                continue
            if required_columns.issubset(set(dataframe.columns)):
                selected = dataframe.copy()
                selected.attrs["table_name"] = table_name
                return selected

        raise DataSourceError(
            "Default table does not contain the columns required by the execution plan",
            details={
                "table_name": self._settings.default_table,
                "required_columns": sorted(required_columns),
            },
        )

    def _required_columns(
        self,
        *,
        plan: ExecutionPlan,
        knowledge_context: KnowledgeContext,
    ) -> set[str]:
        columns: set[str] = set()
        metric_names = {metric.name for metric in plan.metrics}
        entity_names = {entity.name for entity in plan.entities}
        is_campaign_detail = plan.intent in {"campaign_detail", "campaign_summary"}
        if is_campaign_detail:
            return set(self._REQUIRED_COLUMNS_CAMPAIGN_DETAIL)

        for metric in knowledge_context.metrics:
            if metric.name in metric_names and metric.column is not None:
                columns.add(metric.column)
            if metric.name == "quantidade_compras" and "ticket_medio" in metric_names:
                columns.add(metric.column or "")
            if metric.name == "faturamento" and "ticket_medio" in metric_names:
                columns.add(metric.column or "")

        for dimension in knowledge_context.dimensions:
            if dimension.name in entity_names or any(
                operation.field == dimension.name for operation in plan.operations
            ):
                column = dimension.column or dimension.key or dimension.derived_from
                if column is not None:
                    columns.add(column)

        for operation in plan.operations:
            if operation.type in {"filter", "group_by"} and operation.field is not None:
                columns.add(
                    self._resolve_dimension_column(
                        operation.field,
                        knowledge_context=knowledge_context,
                    ),
                )

            end_field = operation.parameters.get("end_field")
            if isinstance(end_field, str):
                columns.add(end_field)

            if operation.type != "campaign_detail" and not (
                plan.intent == "metric_query" and operation.type == "select"
            ):
                fields = operation.parameters.get("fields", [])
                if isinstance(fields, list):
                    columns.update(field for field in fields if isinstance(field, str))

            subset = operation.parameters.get("subset", [])
            if isinstance(subset, list):
                columns.update(field for field in subset if isinstance(field, str))

            metrics = operation.parameters.get("metrics", [])
            if isinstance(metrics, list):
                for metric in metrics:
                    if isinstance(metric, dict) and isinstance(metric.get("field"), str):
                        columns.add(metric["field"])

        return {column for column in columns if column}

    def _resolve_dimension_column(
        self,
        name: str,
        *,
        knowledge_context: KnowledgeContext,
    ) -> str:
        for dimension in knowledge_context.dimensions:
            if dimension.name == name:
                return dimension.column or dimension.key or dimension.derived_from or name

        return name

    def _routed_response(
        self,
        question: str,
        *,
        response: str,
        response_type: str,
    ) -> ExecuteResponse:
        return ExecuteResponse(
            question=question,
            answer=response,
            highlights=[],
            insights=[],
            recommendations=[],
            data=[],
            metadata={"data_accessed": False, "response_type": response_type},
            warnings=[],
        )

    def _sanitize_rows(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                key: value
                for key, value in row.items()
                if self._normalize_text(key) not in self._SENSITIVE_COLUMNS
            }
            for row in rows
        ]

    def _log_composite_filter_validation(
        self,
        *,
        question: str,
        plan: ExecutionPlan,
        result: object,
    ) -> None:
        normalized_question = self._normalize_text(question)
        expected_fields: set[str] = set()
        if "campanha" in normalized_question or "promocao" in normalized_question:
            expected_fields.add("nm_promocao")
        if "loja" in normalized_question or "casas bahia" in normalized_question:
            expected_fields.add("nm_fantasa")
        if "segmento" in normalized_question:
            expected_fields.add("nm_segmento")
        if "bairro" in normalized_question:
            expected_fields.add("bairro")
        if "cidade" in normalized_question:
            expected_fields.add("cidade")
        if "shopping" in normalized_question or "empreendimento" in normalized_question:
            expected_fields.add("nm_empreendimento")

        if len(expected_fields) < 2:
            return

        applied_fields = {
            operation.field
            for operation in plan.operations
            if operation.type == "filter" and operation.field is not None
        }
        applied_fields.update(
            operation.field
            for operation in plan.operations
            if operation.type == "group_by" and operation.field is not None
        )
        missing_fields = expected_fields.difference(applied_fields)
        if not missing_fields:
            return

        logger.warning(
            "Possible composite filter loss after execution. "
            "question=%s expected=%s applied=%s rows=%s",
            question,
            sorted(expected_fields),
            sorted(applied_fields),
            getattr(result, "rows_returned", None),
        )

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )
        alphanumeric_text = re.sub(r"[^a-z0-9_]+", " ", without_accents)
        return re.sub(r"\s+", " ", alphanumeric_text).strip()
