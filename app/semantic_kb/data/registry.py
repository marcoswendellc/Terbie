from app.semantic_kb.data.business_rules import KB_BUSINESS_RULES
from app.semantic_kb.data.calculated_fields import KB_CALCULATED_FIELDS
from app.semantic_kb.data.contexts import KB_CONTEXTS
from app.semantic_kb.data.dimensions import KB_DIMENSIONS
from app.semantic_kb.data.disambiguation import KB_DISAMBIGUATION_RULES
from app.semantic_kb.data.examples import KB_EXAMPLES
from app.semantic_kb.data.intents import KB_INTENTS
from app.semantic_kb.data.metrics import KB_METRICS
from app.semantic_kb.data.priorities import KB_PRIORITIES
from app.semantic_kb.data.relationships import KB_RELATIONSHIPS
from app.semantic_kb.data.response_rules import KB_RESPONSE_RULES
from app.semantic_kb.models import SemanticKnowledgeBase

SEMANTIC_KNOWLEDGE_BASE = SemanticKnowledgeBase(
    version="2026.07.07",
    metrics=KB_METRICS,
    dimensions=KB_DIMENSIONS,
    intents=KB_INTENTS,
    business_rules=KB_BUSINESS_RULES,
    response_rules=KB_RESPONSE_RULES,
    calculated_fields=KB_CALCULATED_FIELDS,
    relationships=KB_RELATIONSHIPS,
    contexts=KB_CONTEXTS,
    priorities=KB_PRIORITIES,
    disambiguation_rules=KB_DISAMBIGUATION_RULES,
    examples=KB_EXAMPLES,
    column_mappings={
        "faturamento": "vl_compra",
        "quantidade_compras": "cd_compra",
        "clientes_unicos": "sk_cliente",
        "ticket_medio_por_compra": ["vl_compra", "cd_compra"],
        "ticket_medio_por_cliente": ["vl_compra", "sk_cliente"],
        "campanha": "nm_promocao",
        "promocao": "nm_promocao",
        "acao": "nm_promocao",
        "evento promocional": "nm_promocao",
        "segmento": "nm_segmento",
        "loja": "nm_fantasa",
        "bairro": "bairro",
        "cidade": "cidade",
        "empreendimento": "nm_empreendimento",
        "periodo_inicio": "sk_dtinicio",
        "periodo_fim": "sk_dtfim",
        "periodo da campanha": ["sk_dtinicio", "sk_dtfim"],
    },
    metric_resolution={
        "ticket_medio": {
            "default": "ticket_medio_por_compra",
            "available": ["ticket_medio_por_compra", "ticket_medio_por_cliente"],
            "ambiguity_policy": "prefer_default",
        },
    },
    response_best_practices=[
        "Usar linguagem natural, clara e objetiva.",
        "Nao expor detalhes tecnicos internos ao usuario final.",
        "Nao repetir exatamente a mesma frase em destaques.",
        "Em listagens, mostrar os itens encontrados e nao apenas a contagem.",
    ],
)
