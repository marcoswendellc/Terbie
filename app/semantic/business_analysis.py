"""Recognize explicit, supported business questions without model rewrites."""

import re

from app.semantic.temporal import normalize_temporal_text

TITLES = {
    "weekday": "Faturamento e compras por dia da semana",
    "frequency": "Frequência de compras por cliente",
    "concentration": "Participação dos clientes de maior gasto",
    "ticket_evolution": "Evolução diária do ticket médio",
    "age_metrics": "Ticket e frequência por faixa etária",
    "purchase_repeat": "Clientes com uma ou múltiplas compras",
    "age_segments": "Consumo de segmentos por faixa etária",
    "geo_ranking": "Clientes e faturamento por localização",
    "geo_ticket": "Ticket por localização",
    "outside_city": "Clientes residentes fora da cidade do shopping",
    "neighborhood_frequency": "Frequência de compras por bairro",
    "segment_share": "Participação dos segmentos",
    "store_customers": "Clientes únicos por loja",
    "segment_recurrence": "Ticket e recorrência por segmento",
    "segment_pairs": "Combinações de segmentos por cliente",
    "campaign_ranking": "Indicadores por campanha",
    "campaign_frequency": "Frequência e gasto por cliente em cada campanha",
    "campaign_phases": "Participação no início, meio e fim da campanha",
    "campaign_retention": "Participação de clientes em múltiplas campanhas",
}


def business_analysis_mode(question):
    text = normalize_temporal_text(question)
    rules = [
        ("weekday", r"\bdias? da semana\b"),
        ("concentration", r"10\s*%.*clientes|clientes.*10\s*%"),
        ("campaign_retention", r"(?:mais de uma|multiplas|varias) campanhas?"),
        ("campaign_phases", r"inicio.*meio.*fim"),
        ("segment_pairs", r"combinacoes?.*segmentos|segmentos.*combinacoes?"),
        ("outside_city", r"fora da cidade.*shopping|fora.*cidade.*empreendimento"),
        ("purchase_repeat", r"(?:apenas|somente) uma compra|uma compra.*multiplas"),
        ("age_segments", r"segmentos.*faixa.*etaria|faixa.*etaria.*segmentos"),
        ("age_metrics", r"faixa.*etaria.*ticket.*frequencia|faixa.*etaria.*frequencia.*ticket"),
        ("segment_recurrence", r"segmentos.*tickets?.*(?:recorrencia|frequencia)"),
        ("segment_share", r"segmentos.*participacao.*(?:faturamento|compras)"),
        ("store_customers", r"lojas.*(?:atrair|clientes unicos)"),
        ("neighborhood_frequency", r"bairros.*frequencia"),
        ("geo_ranking", r"bairros.*cidades.*(?:clientes|faturamento)"),
        ("geo_ticket", r"regioes.*ticket"),
        ("campaign_frequency", r"campanhas.*frequencia.*ticket"),
        ("campaign_ranking", r"campanhas.*faturamento.*(?:quantidade de )?compras.*clientes"),
        ("ticket_evolution", r"ticket.*(?:evolui|evolucao|ao longo)"),
        ("frequency", r"\bfrequencia\b.*\bcompras\b|"
                      r"\bcompras\s+por\s+(?:clientes?|pessoas?|consumidores?)\b"),
    ]
    return next((mode for mode, pattern in rules if re.search(pattern, text)), None)


def frequency_breakdown(question):
    text = normalize_temporal_text(question)
    return {
        "by_shopping": bool(re.search(
            r"\b(?:(?:por|cada)\s+(?:shopping|empreendimento)s?|"
            r"(?:shoppings|empreendimentos))\b", text,
        )),
        "by_month": bool(re.search(r"\b(?:por mes|mensal|mensalmente|mes a mes)\b", text)),
    }


def explicit_business_scope(question):
    text = normalize_temporal_text(question)
    shopping = None
    for match in re.finditer(r"(?=\b(?:no|do|na|da)\s+([^?;!.]+))", text):
        candidate = re.split(r"\s+(?:na|no|da|do|em|durante)\b", match.group(1))[0].strip()
        if (
            re.search(r"\bshopping\b", candidate)
            and candidate != "shopping"
            and not re.search(r"\b(cidade|onde|campanha|promocao)\b", candidate)
        ):
            shopping = candidate
    campaign_match = re.search(
        r"\b(?:na|da|durante a|para a)\s+(?:campanha|promocao)\s+(?:de\s+)?"
        r"([^?;!.]+)",
        text,
    )
    campaign = campaign_match.group(1).strip(' "') if campaign_match else None
    if campaign and shopping:
        campaign = re.split(r"\s+(?:no|na|do|da)\s+" + re.escape(shopping), campaign)[0]
    if campaign:
        campaign = re.split(
            r"\s+em\s+(?=\d|janeiro|fevereiro|marco|abril|maio|junho|julho|"
            r"agosto|setembro|outubro|novembro|dezembro)",
            campaign,
        )[0].strip()
    if campaign in {"promocional", "atual", "analisada", "selecionada"}:
        campaign = None
    limit = re.search(r"\btop\s+(\d+)\b", text)
    return {
        "campaign": campaign,
        "shopping": shopping,
        "limit": min(int(limit.group(1)), 1000) if limit else None,
    }
