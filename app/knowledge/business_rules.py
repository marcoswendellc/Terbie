from app.knowledge.models import BusinessRule
from app.knowledge.shopping_aliases import SHOPPING_ALIASES

BUSINESS_RULES: list[BusinessRule] = [
    BusinessRule(
        code="purchasing_percentile_score",
        description=(
            "Para lojas, clientes e bairros mais representativos ou engajados, sem critério "
            "explícito, usar score composto pela média ponderada dos percentis de faturamento, "
            "quantidade de compras únicas e ticket médio por compra, com pesos iguais por padrão. "
            "Métrica explícita prevalece sobre score implícito. Aplicar shopping, campanha, "
            "período e permissões antes de calcular; top N somente depois dos percentis de toda "
            "a população elegível. Percentil = 100 * (posição média - 1) / (n - 1); "
            "empates recebem a posição média; apenas uma entidade tem score indefinido. "
            "Score é pontuação relativa de 0 a 100, não participação ou probabilidade. "
            "Ticket = faturamento/compras: componentes relacionados. Para clientes, descrever "
            "engajamento em compras registradas e usar referências anônimas do recorte. "
            "Mostrar indicadores, percentis, pesos e tamanho da população."
        ),
        fields=["vl_compra", "cd_compra", "sk_cliente", "nm_fantasa", "bairro"],
        concepts=["score", "representatividade", "engajamento"],
    ),
    BusinessRule(
        code="shopping_nicknames",
        description=(
            "Apelidos oficiais dos shoppings: "
            + "; ".join(f"{alias} = {name}" for alias, name in SHOPPING_ALIASES.items())
            + ". Use o nome completo nos filtros de nm_empreendimento. "
            "POR identifica Portal Shopping apenas em maiúsculas; "
            "a preposição por não identifica um shopping."
        ),
        fields=["nm_empreendimento"],
        concepts=["empreendimento", "apelido"],
    ),
    BusinessRule(
        code="purchase_date",
        description="dt_registro_mos é a data da compra.",
        fields=["dt_registro_mos"],
        concepts=["compra", "tempo"],
    ),
    BusinessRule(
        code="promotion_dates",
        description="sk_dtinicio e sk_dtfim são datas de início e fim da promoção, não da compra.",
        fields=["sk_dtinicio", "sk_dtfim"],
        concepts=["promocao", "tempo"],
    ),
    BusinessRule(
        code="loyalty_purchase",
        description="Se cd_promocao for nulo, a compra deve ser considerada compra de fidelidade.",
        fields=["cd_promocao"],
        concepts=["tipo_compra", "fidelidade"],
    ),
    BusinessRule(
        code="promotional_purchase",
        description="Se cd_promocao não for nulo, a compra pode estar associada a promoção.",
        fields=["cd_promocao"],
        concepts=["tipo_compra", "promocional"],
    ),
    BusinessRule(
        code="loyalty_promotional_purchase",
        description="Uma mesma compra pode estar associada ao fidelidade e à promoção.",
        fields=["cd_compra", "cd_promocao"],
        concepts=["tipo_compra", "fidelidade_promocional"],
    ),
    BusinessRule(
        code="promotion_period_analysis",
        description=(
            "Compras promocionais devem ser analisadas pelo período da promoção "
            "quando a pergunta mencionar promoção/campanha."
        ),
        fields=["sk_dtinicio", "sk_dtfim"],
        concepts=["promocao", "campanha"],
    ),
    BusinessRule(
        code="general_purchase_period_analysis",
        description="Compras gerais devem ser analisadas por dt_registro_mos.",
        fields=["dt_registro_mos"],
        concepts=["compra", "faturamento"],
    ),
    BusinessRule(
        code="purchase_type_classification",
        description=(
            "Classificação conceitual tipo_compra: "
            "fidelidade, promocional, fidelidade_promocional."
        ),
        fields=["cd_promocao"],
        concepts=["tipo_compra", "fidelidade", "promocional", "fidelidade_promocional"],
    ),
]
