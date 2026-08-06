import re
import unicodedata

from app.knowledge.models import KnowledgeContext
from app.query_plan.models import MultiQueryPlan, QueryPlan
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService


class MultiQueryPlanner:
    """Decomposes compound questions and compiles each request independently."""

    _METRIC_START = re.compile(
        r"\s+e\s+(?=(?:o|a)?\s*(?:ticket|faturamento|receita|vendas|"
        r"quantidade|volume|clientes))",
        flags=re.IGNORECASE,
    )
    _CAMPAIGN_CONTEXT = re.compile(
        r"\b(?:na|no|da|do)\s+campanha\s+(.+?)(?:[.?!]|$)",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        semantic_service: SemanticService,
        planner_service: PlannerService,
    ) -> None:
        self._semantic_service = semantic_service
        self._planner_service = planner_service

    def build(
        self,
        *,
        question: str,
        knowledge_context: KnowledgeContext,
    ) -> MultiQueryPlan | None:
        requests = self.decompose(question)
        if len(requests) < 2:
            return None

        plans = [
            self._compile_request(
                request_id=f"query_{index}",
                question=request,
                knowledge_context=knowledge_context,
            )
            for index, request in enumerate(requests, start=1)
        ]
        return MultiQueryPlan(question=question, plans=plans)

    def decompose(self, question: str) -> list[str]:
        clauses = [item.strip(" ,") for item in self._METRIC_START.split(question)]
        if len(clauses) < 2:
            return [question]
        normalized_question = self._normalize(question)
        has_independent_scope = any(
            marker in normalized_question
            for marker in (
                " geral",
                " total",
                " independentemente do segmento",
            )
        )
        first_clause = self._normalize(clauses[0])
        has_ranked_or_dimensioned_request = any(
            marker in first_clause
            for marker in ("top ", "ranking", "loja", "lojista", "segmento")
        )
        if not (has_independent_scope and has_ranked_or_dimensioned_request):
            return [question]

        campaign_match = self._CAMPAIGN_CONTEXT.search(question)
        campaign_context = campaign_match.group(0).strip(" .?!") if campaign_match else None
        requests: list[str] = []
        for clause in clauses:
            if campaign_context and "campanha" not in self._normalize(clause):
                clause = f"{clause} {campaign_context}"
            requests.append(clause.strip(" .") + ".")
        return requests

    def _compile_request(
        self,
        *,
        request_id: str,
        question: str,
        knowledge_context: KnowledgeContext,
    ) -> QueryPlan:
        semantic_resolution = self._semantic_service.resolve(question=question)
        response = self._planner_service.create_draft_plan(
            question=question,
            semantic_resolution=semantic_resolution,
            knowledge_context=knowledge_context,
        )
        execution_plan = response.plan
        metric = execution_plan.metrics[0].name if execution_plan.metrics else ""
        dimensions = [
            operation.field
            for operation in execution_plan.operations
            if operation.type == "group_by" and operation.field is not None
        ]
        filters = [
            {
                "field": operation.field,
                "operator": operation.parameters.get("operator", "equals"),
                "value": operation.parameters.get("value"),
            }
            for operation in execution_plan.operations
            if operation.type == "filter" and operation.field is not None
        ]
        sort = next(
            (operation for operation in execution_plan.operations if operation.type == "sort"),
            None,
        )
        limit = next(
            (
                operation.parameters.get("value")
                for operation in execution_plan.operations
                if operation.type == "limit"
            ),
            None,
        )
        limit_value = limit if isinstance(limit, int) else None
        return QueryPlan(
            id=request_id,
            title=self._title(metric=metric, dimensions=dimensions),
            metric=metric,
            dimensions=dimensions,
            filters=filters,
            order_by=sort.field if sort else None,
            order=sort.parameters.get("direction") if sort else None,
            top=limit_value,
            limit=limit_value,
            question=question,
            execution_plan=execution_plan,
        )

    def _title(self, *, metric: str, dimensions: list[str]) -> str:
        metric_labels = {
            "faturamento": "Faturamento",
            "ticket_medio": "Ticket médio por compra",
            "ticket_medio_por_compra": "Ticket médio por compra",
            "quantidade_compras": "Quantidade de compras",
            "clientes_unicos": "Clientes únicos",
        }
        if dimensions:
            dimension_labels = {"nm_fantasa": "lojas", "nm_segmento": "segmentos"}
            dimension = dimension_labels.get(dimensions[0], dimensions[0])
            return f"Ranking de {dimension} por {metric_labels.get(metric, metric).lower()}"
        return metric_labels.get(metric, metric.replace("_", " ").title())

    def _normalize(self, text: str) -> str:
        return "".join(
            character
            for character in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(character)
        )
