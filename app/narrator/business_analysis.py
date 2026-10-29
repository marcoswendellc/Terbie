"""Portuguese tables and explicit definitions for deterministic business analyses."""

from app.semantic.business_analysis import TITLES

LABELS = {
    "mes": "Mês",
    "nm_promocao": "Campanha",
    "nm_empreendimento": "Shopping",
    "nm_fantasa": "Loja",
    "nm_segmento": "Segmento",
    "faixa_etaria": "Faixa etária",
    "cidade": "Cidade",
    "bairro": "Bairro",
    "uf": "UF",
    "regiao": "Região",
    "dia_semana": "Dia da semana",
    "data_compra": "Data da compra",
    "faturamento": "Faturamento",
    "quantidade_compras": "Compras",
    "clientes_unicos": "Clientes únicos",
    "clientes": "Clientes",
    "ticket_medio_por_compra": "Ticket por compra",
    "ticket_medio_por_cliente": "Gasto por cliente",
    "frequencia_media": "Compras por cliente",
    "receita": "Faturamento",
    "clientes_top_10_pct": "Clientes no grupo dos 10%",
    "receita_top_10_pct": "Gasto do grupo dos 10%",
    "participacao_receita_top_10_pct": "Participação dos 10% no faturamento",
    "perfil_compra": "Perfil de compras",
    "proporcao_clientes": "% dos clientes",
    "segmento_a": "Segmento A",
    "segmento_b": "Segmento B",
    "clientes_em_comum": "Clientes em comum",
    "suporte_pct": "% dos clientes com o par",
    "participacao_faturamento_pct": "% do faturamento",
    "participacao_compras_pct": "% das compras",
    "cidade_shopping": "Cidade do shopping",
    "clientes_cidade_conhecida": "Clientes com cidade",
    "clientes_cidade_desconhecida": "Clientes sem cidade",
    "clientes_fora_cidade": "Clientes de fora",
    "proporcao_fora_cidade_conhecida": "% de fora entre cidades conhecidas",
    "proporcao_cidade_desconhecida": "% sem cidade",
    "fase": "Fase",
    "data_inicio_fase": "Início da fase",
    "data_fim_fase": "Fim da fase",
    "clientes_novos": "Primeira compra na campanha",
    "participacao_clientes": "% dos participantes",
    "participacao_novos_na_fase": "% novos na fase",
    "denominador_clientes": "Clientes no recorte",
    "clientes_multicampanha": "Clientes em várias campanhas",
    "participacao_multicampanha": "% em várias campanhas",
    "data_inicio_campanha": "Início da campanha",
    "clientes_retornantes": "Clientes retornantes",
    "gasto_medio_retornantes": "Gasto dos retornantes nesta campanha",
    "gasto_medio_retornantes_anterior": "Gasto dos mesmos clientes antes",
    "variacao_gasto_retornantes": "Variação do gasto dos mesmos clientes",
    "frequencia_media_retornantes": "Frequência dos retornantes",
    "frequencia_media_retornantes_anterior": "Frequência dos mesmos clientes antes",
    "variacao_frequencia_retornantes": "Variação da frequência",
    "nivel_geografico": "Nível geográfico",
    "uf_shopping": "UF do shopping",
    "clientes_cidade_conflitante": "Clientes com residência conflitante",
    "denominador_clientes_campanha": "Clientes da campanha",
}
HIDDEN = {
    "cd_promocao",
    "cd_empreendimento",
    "sk_loja",
    "sk_dtinicio",
    "sk_dtfim",
    "dia_semana_ordem",
    "fase_ordem",
    "status",
    "detail",
    "modo",
}
MONEY = {
    "faturamento",
    "receita",
    "receita_top_10_pct",
    "ticket_medio_por_compra",
    "ticket_medio_por_cliente",
    "gasto_medio_retornantes",
    "gasto_medio_retornantes_anterior",
    "variacao_gasto_retornantes",
}
STATUS = {
    "missing_shopping_city": "Falta o cadastro da cidade do shopping para distinguir "
    "clientes locais "
    "e de fora. A cidade do shopping não será inferida a partir dos clientes.",
    "missing_dimension": "A base não contém a dimensão necessária para este recorte.",
    "periodo_campanha_indisponivel": "Há campanha sem datas válidas de início/fim; suas fases não "
    "foram calculadas.",
    "ordem_cronologica_indisponivel": "Faltam datas de início para ordenar "
    "a evolução entre campanhas.",
}


def _leaders(mode, rows):
    if mode == "geo_ranking":
        return [
            level.capitalize() + ": " + description
            for level in ("cidade", "bairro")
            for description in _leaders(
                "geo_" + level, [row for row in rows if row.get("nivel_geografico") == level]
            )
        ]
    metrics = {
        "geo_cidade": ("clientes_unicos", "faturamento"),
        "geo_bairro": ("clientes_unicos", "faturamento"),
        "weekday": ("faturamento", "quantidade_compras"),
        "age_metrics": ("ticket_medio_por_compra", "frequencia_media"),
        "geo_ticket": ("ticket_medio_por_compra",),
        "neighborhood_frequency": ("frequencia_media",),
        "segment_recurrence": ("ticket_medio_por_compra", "frequencia_media"),
        "segment_share": ("participacao_faturamento_pct", "participacao_compras_pct"),
        "store_customers": ("clientes_unicos",),
        "campaign_ranking": ("faturamento", "quantidade_compras", "clientes_unicos"),
        "campaign_frequency": ("frequencia_media", "ticket_medio_por_cliente"),
    }.get(mode, ())
    identities = {
        "geo_cidade": ("uf", "cidade"),
        "geo_bairro": ("uf", "cidade", "bairro"),
        "weekday": ("dia_semana",),
        "age_metrics": ("faixa_etaria",),
        "geo_ticket": ("regiao", "uf", "cidade"),
        "neighborhood_frequency": ("uf", "cidade", "bairro"),
        "segment_recurrence": ("nm_segmento",),
        "segment_share": ("nm_segmento",),
        "store_customers": ("nm_fantasa", "nm_empreendimento"),
        "campaign_ranking": ("nm_promocao", "nm_empreendimento"),
        "campaign_frequency": ("nm_promocao", "nm_empreendimento"),
    }.get(mode, ())
    names = {
        "frequencia_media": "frequência",
        "ticket_medio_por_compra": "ticket por compra",
        "ticket_medio_por_cliente": "gasto por cliente",
    }
    descriptions = []
    for metric in metrics:
        primary = {
            "geo_cidade": ("cidade",),
            "geo_bairro": ("bairro",),
            "geo_ticket": ("regiao", "cidade"),
            "neighborhood_frequency": ("bairro",),
            "store_customers": ("nm_fantasa",),
            "campaign_ranking": ("nm_promocao",),
            "campaign_frequency": ("nm_promocao",),
        }.get(mode, identities)
        candidates = [
            row
            for row in rows
            if isinstance(row.get(metric), int | float)
            and any(row.get(field) not in {None, "Não informado"} for field in primary)
        ]
        if not candidates:
            continue
        maximum = max(row[metric] for row in candidates)
        labels = list(
            dict.fromkeys(
                " — ".join(str(row[field]) for field in identities if row.get(field) is not None)
                for row in candidates
                if row[metric] == maximum
            )
        )
        title = names.get(metric, LABELS.get(metric, metric.replace("_", " ")).lower())
        tie = f" (empate entre {len(labels)} grupos)" if len(labels) > 1 else ""
        value = (
            " — " + f"{float(maximum):.2f}".replace(".", ",") + " compras por cliente"
            if mode == "neighborhood_frequency" and metric == "frequencia_media" else ""
        )
        descriptions.append(f"Maior {title}: " + "; ".join(labels[:5]) + value + tie + ".")
    return descriptions


def business_analysis_answer(context, formatter):
    metadata = context.execution_metadata["business_analysis"]
    mode = metadata["mode"]
    parts = [TITLES.get(mode, "Análise de compras registradas") + "."]
    resolved = context.execution_metadata.get("resolved_entities", {})
    scope = [
        str(resolved[field])
        for field in ("nm_promocao", "nm_empreendimento")
        if resolved.get(field)
    ]
    if scope:
        parts.append("Recorte: " + " — ".join(scope) + ".")
    for item in metadata.get("scope", []):
        if item.get("field") == "dt_registro_mos":
            parts.append(f"Compras de {item['value']} a {item.get('end_value', item['value'])}.")
    statuses = {row.get("status") for row in context.data}
    for status in sorted(value for value in statuses if value):
        if status in STATUS:
            parts.append(STATUS[status])
    for row in context.data:
        if row.get("detail"):
            parts.append(row["detail"])
    parts.extend(_leaders(mode, context.data))
    if mode == "campaign_retention" and context.data:
        first = context.data[0]
        if first.get("participacao_multicampanha") is not None:
            parts.append(
                f"{first['clientes_multicampanha']} de {first['denominador_clientes']} "
                "clientes identificados participaram de mais de uma campanha "
                f"({first['participacao_multicampanha'] * 100:.2f}%).".replace(".", ",", 1)
            )
    columns = list(dict.fromkeys(key for row in context.data for key in row if key not in HIDDEN))
    if mode == "neighborhood_frequency" and "frequencia_media" in columns:
        first = [key for key in ("uf", "cidade", "bairro", "frequencia_media") if key in columns]
        columns = [*first, *[key for key in columns if key not in first]]

    def cell(column, value):
        if value is None:
            return "Não disponível"
        if column == "perfil_compra":
            return {"compra_unica": "Uma compra", "multiplas_compras": "Múltiplas compras"}.get(
                value, str(value)
            )
        if column in MONEY:
            return formatter.value("faturamento", value)
        if column == "frequencia_media":
            return f"{float(value):.2f}".replace(".", ",")
        if (
            column.startswith("proporcao_")
            or column.startswith("participacao_")
            and not (column.endswith("_pct"))
        ):
            return f"{float(value) * 100:.2f}%".replace(".", ",")
        if column.endswith("_pct") and column not in {"clientes_top_10_pct", "receita_top_10_pct"}:
            return f"{float(value):.2f}%".replace(".", ",")
        if isinstance(value, float):
            return f"{value:.2f}".replace(".", ",")
        return str(value).replace("|", "/").replace("\n", " ")

    if columns:
        table = [
            "| "
            + " | ".join(LABELS.get(key, key.replace("_", " ").capitalize()) for key in columns)
            + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        shown = context.data[:100]
        if mode == "geo_ranking":
            shown = [
                row
                for level in ("cidade", "bairro")
                for row in [item for item in context.data if item.get("nivel_geografico") == level][
                    :50
                ]
            ]
        for row in shown:
            table.append("| " + " | ".join(cell(key, row.get(key)) for key in columns) + " |")
        parts.append("\n".join(table))
        if len(context.data) > len(shown):
            parts.append(
                f"Exibindo {len(shown)} de {len(context.data)} grupos"
                + (" (até 50 por nível geográfico). " if mode == "geo_ranking" else ". ")
                + "Restrinja o shopping, a campanha ou o período para detalhar o recorte."
            )
    parts.extend(metadata.get("notes", []))
    parts.append(
        "Frequência = compras únicas por cliente identificado. Ticket por compra = "
        "faturamento/compras. Gasto por cliente considera apenas compras com cliente "
        "identificado. Os dados descrevem compras registradas, não todos os visitantes "
        "ou atração causal das lojas."
    )
    return "\n\n".join(dict.fromkeys(parts))
