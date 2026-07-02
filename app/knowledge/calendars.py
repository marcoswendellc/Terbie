from app.knowledge.models import BusinessCalendar

BUSINESS_CALENDARS: list[BusinessCalendar] = [
    BusinessCalendar(
        name="calendario_compra",
        primary_field="dt_registro_mos",
        fields=["dt_registro_mos"],
        used_for=["vendas", "clientes", "lojas", "segmentos"],
    ),
    BusinessCalendar(
        name="calendario_promocao",
        fields=["sk_dtinicio", "sk_dtfim"],
        used_for=["promoção", "campanha", "ação promocional"],
    ),
]
