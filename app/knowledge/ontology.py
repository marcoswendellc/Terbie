from app.knowledge.models import BusinessEntity

BUSINESS_ENTITIES: list[BusinessEntity] = [
    BusinessEntity(name="Compra", fields=["cd_compra", "vl_compra", "dt_registro_mos"]),
    BusinessEntity(name="Cliente", fields=["sk_cliente", "tx_cep", "uf", "bairro"]),
    BusinessEntity(name="Loja", fields=["sk_loja", "nm_fantasa", "nm_segmento"]),
    BusinessEntity(name="Empreendimento", fields=["cd_empreendimento", "nm_empreendimento"]),
    BusinessEntity(
        name="Promoção",
        fields=["cd_promocao", "nm_promocao", "sk_dtinicio", "sk_dtfim"],
    ),
    BusinessEntity(name="Geografia", fields=["tx_cep", "uf", "bairro"]),
    BusinessEntity(name="Tempo", fields=["dt_registro_mos"]),
]
