from app.knowledge.models import BusinessHierarchy

BUSINESS_HIERARCHIES: list[BusinessHierarchy] = [
    BusinessHierarchy(name="empreendimento_loja", levels=["Empreendimento", "Loja"]),
    BusinessHierarchy(
        name="categoria_subcategoria_loja",
        levels=["Categoria", "Subcategoria", "Loja"],
    ),
    BusinessHierarchy(name="promocao_compra", levels=["Promoção", "Compra"]),
    BusinessHierarchy(name="uf_bairro_cliente", levels=["UF", "Bairro", "Cliente"]),
    BusinessHierarchy(name="cliente_compra", levels=["Cliente", "Compra"]),
]
