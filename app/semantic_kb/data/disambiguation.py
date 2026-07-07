from app.semantic_kb.models import KBDisambiguationRule

KB_DISAMBIGUATION_RULES: list[KBDisambiguationRule] = [
    KBDisambiguationRule(
        id="generic_ticket_defaults_to_purchase_ticket",
        description="Ticket medio generico usa ticket medio por compra como padrao configurado.",
        terms=["ticket medio", "ticket médio", "ticket", "ticket medio da campanha"],
        prefer="ticket_medio_por_compra",
        when={"metric": "ticket_medio", "policy": "prefer_default"},
    ),
    KBDisambiguationRule(
        id="campanha_maps_to_promocao",
        description="Campanha, promocao, acao e evento promocional referem-se a promocao.",
        terms=["campanha", "promocao", "acao", "evento promocional"],
        prefer="promocao",
        when={"domain": "marketing"},
    ),
    KBDisambiguationRule(
        id="melhor_campanha_defaults_to_revenue",
        description="Melhor campanha usa faturamento se o usuario nao informar outra metrica.",
        terms=["melhor campanha", "maior campanha"],
        prefer="faturamento",
        when={"entity": "promocao", "metric": None},
    ),
    KBDisambiguationRule(
        id="participacao_defaults_to_purchase_volume",
        description=(
            "Maior participacao sem outro indicador explicito usa volume de notas "
            "como metrica padrao."
        ),
        terms=["participacao", "participaÃ§Ã£o", "maior participacao", "maior participaÃ§Ã£o"],
        prefer="quantidade_compras",
        when={"intent": "ranking", "metric": None},
    ),
]
