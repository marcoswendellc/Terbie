"""Count campaign identities independently of purchase/customer measures."""

import pandas as pd

from app.executor.dates import date_series
from app.executor.operations.business_common import note
from app.semantic.temporal import normalize_temporal_text


def count_campaigns(dataframe, context):
    data = dataframe.copy()
    for field in ("cd_promocao", "cd_empreendimento", "nm_empreendimento"):
        if field in data:
            data[field] = data[field].astype("string").str.strip()
            data[field] = data[field].mask(data[field].str.casefold().isin(
                ["", "null", "none", "nan", "não informado", "nao informado"],
            ))
    campaign = data.cd_promocao.str.replace(r"\.0$", "", regex=True)
    names = data.nm_empreendimento.map(
        lambda value: normalize_temporal_text(str(value)) if pd.notna(value) else pd.NA,
    )
    shops = (
        data.cd_empreendimento.str.replace(r"\.0$", "", regex=True)
        if "cd_empreendimento" in data else pd.Series(pd.NA, index=data.index)
    )
    identities = pd.DataFrame({"name": names, "identity": shops}).dropna()
    mapping = identities.groupby("name").identity.agg(
        lambda values: values.iloc[0] if values.nunique() == 1 else pd.NA,
    )
    shops = shops.fillna(names.map(mapping)).fillna("nome:" + names)
    valid = campaign.notna() & shops.notna()
    if "sk_dtinicio" in data and "sk_dtfim" in data:
        start, end = date_series(data.sk_dtinicio), date_series(data.sk_dtfim)
        valid &= start.notna() & end.notna() & start.le(end)
    result = pd.DataFrame({"shopping": shops, "campaign": campaign})
    count = len(result.loc[valid].drop_duplicates())
    note(context, "Cada campanha identificada é contada uma vez por shopping, "
         "independentemente da quantidade de compras. Campanhas com vigência em qualquer "
         "parte do ano solicitado são incluídas, mesmo que tenham começado no ano anterior.")
    note(context, "A contagem descreve as campanhas identificadas na base disponível; "
         "registros sem identificação e períodos inválidos não entram na contagem.")
    return pd.DataFrame([{"quantidade_campanhas": count}])
