from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult


class ListingInsightAnalyzer:
    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = analytical_plan, execution_plan
        count = execution_result.rows_returned
        columns = list(execution_result.data[0]) if execution_result.data else []
        summary = self._summary(execution_result=execution_result, count=count, columns=columns)
        insight = Insight(
            id="listing_count",
            type="listing",
            title="Quantidade encontrada",
            description=summary,
            value=count,
            metadata={"columns": columns},
        )
        return InsightResult(
            insights=[insight],
            summary=summary,
            recommendations=["Filtrar por periodo", "Comparar itens", "Detalhar por categoria"],
        )

    def _summary(
        self,
        *,
        execution_result: ExecutionResult,
        count: int,
        columns: list[str],
    ) -> str:
        if "nm_promocao" in columns:
            names = [
                str(row["nm_promocao"])
                for row in execution_result.data
                if row.get("nm_promocao") is not None
            ]
            if names:
                count_text = "1 campanha" if count == 1 else f"{count} campanhas"
                return f"Encontrei {count_text}: " + "; ".join(names) + "."

        return f"A listagem retornou {count} item(ns) distintos."

