from pydantic import BaseModel, ConfigDict, Field


class BusinessConcept(BaseModel):
    concept: str
    entity_name: str
    label_fields: list[str]
    key_fields: list[str] = Field(default_factory=list)
    date_fields: list[str] = Field(default_factory=list)
    can_be_filter: bool = True
    can_be_dimension: bool = True

    model_config = ConfigDict(frozen=True)


BUSINESS_CONCEPTS: dict[str, BusinessConcept] = {
    "campanha": BusinessConcept(
        concept="campanha",
        entity_name="promocao",
        label_fields=["nm_promocao"],
        key_fields=["cd_promocao"],
        date_fields=["sk_dtinicio", "sk_dtfim"],
    ),
    "loja": BusinessConcept(
        concept="loja",
        entity_name="loja",
        label_fields=["nm_fantasa"],
        key_fields=["sk_loja"],
    ),
    "segmento": BusinessConcept(
        concept="segmento",
        entity_name="segmento",
        label_fields=["nm_segmento"],
    ),
    "empreendimento": BusinessConcept(
        concept="empreendimento",
        entity_name="empreendimento",
        label_fields=["nm_empreendimento"],
        key_fields=["cd_empreendimento"],
    ),
    "bairro": BusinessConcept(
        concept="bairro",
        entity_name="bairro",
        label_fields=["bairro"],
    ),
    "cidade": BusinessConcept(
        concept="cidade",
        entity_name="cidade",
        label_fields=["cidade"],
    ),
    "cliente": BusinessConcept(
        concept="cliente",
        entity_name="cliente",
        label_fields=["sk_cliente"],
    ),
}
