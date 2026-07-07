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
            return InsightResult(summary="Nao encontrei dados para detalhar essa campanha.")

        row = execution_result.data[0]
        campaign = self._text(row.get("nm_promocao")) or "campanha selecionada"
        summary = self._summary(row=row, campaign=campaign)
        return InsightResult(
            insights=[
                Insight(
                    id="campaign_detail_summary",
                    type="campaign_detail",
                    title="Resumo da campanha",
                    description=summary,
                    entity=campaign,
                    metadata={"response_rule": "campaign_detail_returns_complete_summary"},
                ),
            ],
            summary=summary,
            recommendations=[],
        )

    def _summary(self, *, row: dict[str, object], campaign: str) -> str:
        result_parts = self._result_parts(row)
        ticket_parts = self._ticket_parts(row)
        first_sentence_parts = [*result_parts, *ticket_parts]
        first_sentence = (
            f"Na campanha {campaign}, {self._join(first_sentence_parts)}."
            if first_sentence_parts
            else f"Na campanha {campaign}, encontrei dados para um resumo executivo."
        )

        profile_sentences = self._profile_sentences(row)
        return "\n\n".join([first_sentence, " ".join(profile_sentences)]).strip()

    def _result_parts(self, row: dict[str, object]) -> list[str]:
        parts: list[str] = []
        revenue = self._currency(row.get("faturamento_total"))
        purchases = self._integer(row.get("quantidade_compras"))
        customers = self._integer(row.get("clientes_unicos"))
        if revenue is not None:
            parts.append(f"o faturamento total foi de {revenue}")
        if purchases is not None:
            parts.append(f"com {purchases} compras informadas")
        if customers is not None:
            parts.append(f"{customers} clientes \u00fanicos")
        return parts

    def _ticket_parts(self, row: dict[str, object]) -> list[str]:
        parts: list[str] = []
        ticket_purchase = self._currency(row.get("ticket_medio_por_compra"))
        ticket_customer = self._currency(row.get("ticket_medio_por_cliente"))
        if ticket_purchase is not None:
            parts.append(f"o ticket m\u00e9dio por compra foi de {ticket_purchase}")
        if ticket_customer is not None:
            parts.append(f"o ticket m\u00e9dio por cliente foi de {ticket_customer}")
        return parts

    def _profile_sentences(self, row: dict[str, object]) -> list[str]:
        segment = self._text(row.get("segmento_principal"))
        store = self._text(row.get("loja_maior_faturamento"))
        neighborhood = self._text(row.get("bairro_principal"))
        city = self._text(row.get("cidade_principal"))
        enterprise = self._text(row.get("empreendimento"))
        period = self._period(row)

        sentences: list[str] = []
        if segment and store:
            sentences.append(
                f"O segmento com maior participa\u00e7\u00e3o foi {segment}, "
                f"tendo a loja {store} como principal destaque."
            )
        elif segment:
            sentences.append(f"O segmento com maior participa\u00e7\u00e3o foi {segment}.")
        elif store:
            sentences.append(f"A loja com maior faturamento foi {store}.")

        if neighborhood:
            sentences.append(
                "Desconsiderando registros sem bairro informado, "
                f"o bairro com maior participa\u00e7\u00e3o foi {neighborhood}."
            )
        if city:
            sentences.append(f"A cidade com maior participa\u00e7\u00e3o foi {city}.")

        context_parts: list[str] = []
        if enterprise:
            context_parts.append(f"no {enterprise}")
        if period:
            context_parts.append(period)
        if context_parts:
            sentences.append("A campanha ocorreu " + " ".join(context_parts) + ".")

        return sentences

    def _currency(self, value: object) -> str | None:
        if value is None:
            return None

        return self._formatter.currency_brl(float(value))

    def _integer(self, value: object) -> str | None:
        if value is None:
            return None

        return self._formatter.integer(int(value))

    def _text(self, value: object) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        if text == "" or text.casefold() in {"null", "none", "nan"}:
            return None

        return text

    def _period(self, row: dict[str, object]) -> str:
        start = self._date(row.get("periodo_inicio"))
        end = self._date(row.get("periodo_fim"))
        if start and end:
            return f"entre {start} e {end}"

        return ""

    def _date(self, value: object) -> str | None:
        if value is None:
            return None

        raw_value = str(value).replace(".0", "").strip()
        try:
            return datetime.strptime(raw_value, "%Y%m%d").strftime("%d/%m/%Y")
        except ValueError:
            return raw_value

    def _join(self, parts: list[str]) -> str:
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return " e ".join(parts)
        return ", ".join(parts[:-1]) + " e " + parts[-1]
