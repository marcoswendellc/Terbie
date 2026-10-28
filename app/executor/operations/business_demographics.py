"""Validate purchase demographics without inventing a client's age."""

import pandas as pd

from app.executor.dates import date_series
from app.executor.operations.business_common import note

AGE_GROUPS = ["0-17", "18-24", "25-34", "35-44", "45-59", "60+"]
UNKNOWN = "Não informado"


def derive_age_groups(data, context) -> pd.DataFrame:
    """Preserve receipts and mark implausible or inconsistent ages as unknown."""
    result = data.copy()
    clients = (
        result["sk_cliente"]
        if "sk_cliente" in result
        else pd.Series(pd.NA, index=result.index, dtype="string")
    )
    if "dt_nascimento" in result:
        birth = date_series(result.dt_nascimento).dt.normalize()
        today = pd.Timestamp.now(tz="America/Sao_Paulo").normalize().tz_localize(None)
        before_birthday = (birth.dt.month > today.month) | (
            birth.dt.month.eq(today.month) & birth.dt.day.gt(today.day)
        )
        age = today.year - birth.dt.year - before_birthday.astype(int)
        valid = birth.notna() & birth.le(today) & age.between(0, 120)
        birth = birth.where(valid)
        labels = (
            pd.cut(age.where(valid), bins=[-1, 17, 24, 34, 44, 59, 120], labels=AGE_GROUPS)
            .astype("string")
            .fillna(UNKNOWN)
        )
        values = birth
        note(
            context,
            "Faixa etária calculada na data da análise em America/Sao_Paulo. "
            "Limite operacional: idade entre 0 e 120 anos; datas ausentes, futuras ou "
            "inválidas ficam como Não informado.",
        )
    else:
        raw = (
            result.faixa_etaria.astype("string").str.strip()
            if "faixa_etaria" in result
            else pd.Series(pd.NA, index=result.index, dtype="string")
        )
        labels = raw.where(raw.isin(AGE_GROUPS), UNKNOWN).fillna(UNKNOWN)
        values = labels.where(labels.ne(UNKNOWN))
        note(
            context,
            "Faixas etárias declaradas foram validadas contra os grupos "
            "0-17, 18-24, 25-34, 35-44, 45-59 e 60+; demais valores ficam como Não informado.",
        )
    observations = pd.DataFrame({"client": clients, "value": values})
    counts = observations.loc[observations.client.notna()].groupby("client").value.nunique()
    conflicting = counts.index[counts.gt(1)]
    labels = labels.mask(clients.isin(conflicting), UNKNOWN)
    if len(conflicting):
        note(
            context,
            f"{len(conflicting)} clientes com dados etários válidos conflitantes "
            "foram classificados como Não informado em todas as suas compras. "
            "Nenhuma compra foi excluída por esse motivo.",
        )
    result["faixa_etaria"] = labels
    return result
