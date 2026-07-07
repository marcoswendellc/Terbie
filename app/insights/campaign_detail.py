from datetime import datetime

from app.executor.models import ExecutionResult
from app.insights.models import Insight, InsightResult
from app.narrator.formatter import NarrativeFormatter


class CampaignDetailInsightAnalyzer:
    def __init__(self, formatter: NarrativeFormatter | None = None) -> None:
        self._formatter = formatter or NarrativeFormatter()

    def generate(
        self,
        *,
        execution_result: ExecutionResult,
        analytical_plan: object | None,
        execution_plan: object | None,
    ) -> InsightResult:
        _ = analytical_plan, execution_plan
        if not execution_result.data:
            return InsightResult(summary="Não encontrei dados para detalhar essa campanha.")

        row = execution_result.data[0]
        campaign = row.get("nm_promocao") or "campanha selecionada"
        summary = self._summary(row=row, campaign=str(campaign))
        return InsightResult(
            insights=[
                Insight(
                    id="campaign_detail_summary",
                    type="campaign_detail",
                    title="Resumo da campanha",
                    description=summary,
                    entity=str(campaign),
                    metadata={"response_rule": "campaign_detail_returns_complete_summary"},
                ),
            ],
            summary=summary,
            recommendations=[],
        )

    def _summary(self, *, row: dict[str, object], campaign: str) -> str:
        revenue = self._currency(row.get("faturamento_total"))
        purchases = self._integer_or_unavailable(row.get("quantidade_compras"))
        customers = self._integer_or_unavailable(row.get("clientes_unicos"))
        ticket_purchase = self._currency(row.get("ticket_medio_por_compra"))
        ticket_customer = self._currency(row.get("ticket_medio_por_cliente"))
        segment = row.get("segmento_principal") or "não identificado"
        store = row.get("loja_maior_faturamento") or "não identificada"
        neighborhood = row.get("bairro_principal") or "não identificado"
        city = row.get("cidade_principal") or "não identificada"
        enterprise = row.get("empreendimento") or "não identificado"
        period = self._period(row)
        unavailable = self._unavailable(row)

        return (
            f"Na campanha {campaign}, o faturamento total foi de {revenue}, "
            f"com {purchases} compras informadas e {customers} clientes únicos. "
            f"O ticket médio por compra foi de {ticket_purchase} e o ticket médio "
            f"por cliente foi de {ticket_customer}. "
            f"O segmento com maior participação foi {segment}, com a loja {store} "
            f"como principal destaque em faturamento. O bairro com maior participação "
            f"foi {neighborhood}, a cidade foi {city} e o empreendimento relacionado "
            f"foi {enterprise}.{period}{unavailable}"
        )

    def _currency(self, value: object) -> str:
        if value is None:
            return "não disponível"

        return self._formatter.currency_brl(float(value))

    def _integer_or_unavailable(self, value: object) -> str:
        if value is None:
            return "não disponível"

        return self._formatter.integer(int(value))

    def _unavailable(self, row: dict[str, object]) -> str:
        fields = row.get("campos_indisponiveis")
        if not isinstance(fields, list) or not fields:
            return ""

        return (
            " Alguns campos não estavam disponíveis na base para este resumo: "
            + ", ".join(str(field) for field in fields)
            + "."
        )

    def _period(self, row: dict[str, object]) -> str:
        start = self._date(row.get("periodo_inicio"))
        end = self._date(row.get("periodo_fim"))
        if start and end:
            return f" O período da campanha foi de {start} a {end}."

        return ""

    def _date(self, value: object) -> str | None:
        if value is None:
            return None

        raw_value = str(value).replace(".0", "").strip()
        try:
            return datetime.strptime(raw_value, "%Y%m%d").strftime("%d/%m/%Y")
        except ValueError:
            return raw_value
