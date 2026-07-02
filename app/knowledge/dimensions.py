from app.knowledge.models import BusinessDimension

BUSINESS_DIMENSIONS: list[BusinessDimension] = [
    BusinessDimension(name="loja", column="nm_fantasa", key="sk_loja"),
    BusinessDimension(name="segmento", column="nm_segmento"),
    BusinessDimension(
        name="categoria",
        derived_from="nm_segmento",
        derivation_rule='Texto antes de ">>".',
    ),
    BusinessDimension(
        name="subcategoria",
        derived_from="nm_segmento",
        derivation_rule='Texto depois de ">>".',
    ),
    BusinessDimension(name="cliente", key="sk_cliente"),
    BusinessDimension(name="empreendimento", column="nm_empreendimento", key="cd_empreendimento"),
    BusinessDimension(name="promocao", column="nm_promocao", key="cd_promocao"),
    BusinessDimension(name="bairro", column="bairro"),
    BusinessDimension(name="uf", column="uf"),
    BusinessDimension(name="cep", column="tx_cep"),
    BusinessDimension(name="data_compra", column="dt_registro_mos"),
]
