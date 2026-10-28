"""Calendar and campaign analyses without exposing individual client identifiers."""

import math

import pandas as pd

from app.executor.dates import date_series
from app.executor.operations.business_common import campaign_keys, note, summarize


def _dates(data, column):
    if column not in data:
        return pd.Series(pd.NaT, index=data.index, dtype="datetime64[ns]")
    return date_series(data[column]).dt.normalize()


def _campaigns(data):
    keys = campaign_keys(data)
    if not keys:
        return []
    return [
        (dict(zip(keys, values if isinstance(values, tuple) else (values,), strict=True)), group)
        for values, group in data.groupby(keys, dropna=False, sort=False)
    ]


def _aggregate(data):
    return summarize(data, []).iloc[0].to_dict()


def _boundary(group, column):
    values = _dates(group, column).dropna().unique()
    return pd.Timestamp(values[0]) if len(values) == 1 else None


def _missing(context, status, message):
    note(context, message)
    return pd.DataFrame([{"status": status}])


def _weekday(data, context):
    dates = _dates(data, "dt_registro_mos")
    valid = data.loc[dates.notna()].copy()
    if valid.empty:
        return _missing(
            context,
            "datas_compras_indisponiveis",
            "Não há datas válidas de compra para agrupar por dia da semana.",
        )
    valid["dia_semana_ordem"] = dates.loc[valid.index].dt.dayofweek
    labels = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo",
    ]
    result = summarize(valid, ["dia_semana_ordem"]).sort_values("dia_semana_ordem")
    result.insert(1, "dia_semana", result.dia_semana_ordem.map(dict(enumerate(labels))))
    note(
        context,
        "Totais por dia da semana, sem ajuste pela quantidade de dias observados; "
        "compras sem data válida são excluídas.",
    )
    return result.reset_index(drop=True)


def _ticket_evolution(data, context):
    dates = _dates(data, "dt_registro_mos")
    valid = data.loc[dates.notna()].copy()
    if valid.empty:
        return _missing(
            context,
            "datas_compras_indisponiveis",
            "Não há datas válidas de compra para calcular a evolução diária do ticket.",
        )
    valid["data_compra"] = dates.loc[valid.index].dt.strftime("%Y-%m-%d")
    keys = campaign_keys(valid)
    note(
        context,
        "Ticket diário = faturamento dividido pelas compras do dia. "
        "Dias sem registros e compras sem data válida não são exibidos.",
    )
    return (
        summarize(valid, [*keys, "data_compra"])
        .sort_values([*keys, "data_compra"], na_position="last")
        .reset_index(drop=True)
    )


def _phases(data, context):
    rows = []
    for identity, group in _campaigns(data):
        start, end = _boundary(group, "sk_dtinicio"), _boundary(group, "sk_dtfim")
        if start is None or end is None or end < start:
            rows.append({**identity, "status": "periodo_campanha_indisponivel"})
            continue
        dates = _dates(group, "dt_registro_mos")
        valid = group.loc[dates.between(start, end)].copy()
        valid["__day"] = dates.loc[valid.index]
        duration = (end - start).days + 1
        valid["__phase"] = ((valid.__day - start).dt.days * 3 // duration).astype(int)
        clients = valid.loc[valid.sk_cliente.notna()].groupby("sk_cliente").__day.min()
        first_phase = ((clients - start).dt.days * 3 // duration).astype(int)
        denominator = len(clients)
        for phase, label in enumerate(["Início", "Meio", "Fim"]):
            lower, upper = math.ceil(phase * duration / 3), math.ceil((phase + 1) * duration / 3)
            aggregate = _aggregate(valid.loc[valid.__phase.eq(phase)])
            new = int(first_phase.eq(phase).sum())
            rows.append(
                {
                    **identity,
                    "fase": label,
                    "fase_ordem": phase,
                    "data_inicio_fase": (start + pd.Timedelta(days=lower)).strftime("%Y-%m-%d")
                    if upper > lower
                    else None,
                    "data_fim_fase": (start + pd.Timedelta(days=upper - 1)).strftime("%Y-%m-%d")
                    if upper > lower
                    else None,
                    **aggregate,
                    "clientes_novos": new,
                    "denominador_clientes_campanha": denominator,
                    "participacao_clientes": aggregate["clientes_unicos"] / denominator
                    if denominator
                    else None,
                    "participacao_novos_na_fase": new / aggregate["clientes_unicos"]
                    if aggregate["clientes_unicos"]
                    else None,
                    "status": "ok" if upper > lower else "fase_sem_dias",
                }
            )
    note(
        context,
        "Fases dividem a duração declarada da campanha em três partes de calendário "
        "tão iguais quanto possível, com datas inclusivas; não são inferidas das compras. "
        "Compras sem data ou fora da vigência são excluídas. Clientes novos são os de primeira "
        "compra observada nesta campanha e neste recorte, não necessariamente novos no shopping. "
        "Participação de clientes usa clientes únicos da campanha como denominador; "
        "o mesmo cliente pode participar de várias fases.",
    )
    if not rows or any(row["status"] == "periodo_campanha_indisponivel" for row in rows):
        note(context, "Campanhas sem datas de início/fim únicas e válidas não recebem fases.")
    return (
        pd.DataFrame(rows) if rows else pd.DataFrame([{"status": "periodo_campanha_indisponivel"}])
    )


def _retention(data, context):
    campaigns = _campaigns(data)
    if not campaigns:
        return _missing(
            context,
            "campanhas_indisponiveis",
            "Não há identificadores de campanha disponíveis para medir recorrência.",
        )
    memberships = {}
    for index, (_, group) in enumerate(campaigns):
        for client in group.sk_cliente.dropna().unique():
            memberships.setdefault(client, set()).add(index)
    denominator = len(memberships)
    recurring = sum(len(values) > 1 for values in memberships.values())
    entries = [(identity, group, _boundary(group, "sk_dtinicio")) for identity, group in campaigns]
    chronology = all(start is not None for _, _, start in entries)
    if chronology:
        entries.sort(key=lambda entry: entry[2])
    rows, history = [], {}
    for identity, group, start in entries:
        aggregate = _aggregate(group)
        row = {
            **identity,
            **aggregate,
            "denominador_clientes": denominator,
            "clientes_multicampanha": recurring,
            "participacao_multicampanha": recurring / denominator if denominator else None,
            "data_inicio_campanha": start.strftime("%Y-%m-%d") if start is not None else None,
            "status": "ok" if chronology else "ordem_cronologica_indisponivel",
        }
        if chronology:
            clients = (
                group[group.sk_cliente.notna()]
                .groupby("sk_cliente")
                .agg(gasto=("vl_compra", "sum"), compras=("__purchase", "nunique"))
            )
            prior = {}
            for client in clients.index:
                earlier = [entry for entry in history.get(client, []) if entry[0] < start]
                if earlier:
                    latest_start = max(entry[0] for entry in earlier)
                    latest = [entry for entry in earlier if entry[0] == latest_start]
                    if len(latest) == 1:
                        prior[client] = latest[0]
            returning = list(prior)
            count = len(returning)
            current_spend = float(clients.loc[returning, "gasto"].mean()) if count else None
            prior_spend = sum(prior[client][1] for client in returning) / count if count else None
            current_frequency = float(clients.loc[returning, "compras"].mean()) if count else None
            prior_frequency = (
                sum(prior[client][2] for client in returning) / count if count else None
            )
            row.update(
                {
                    "clientes_retornantes": count,
                    "gasto_medio_retornantes": current_spend,
                    "gasto_medio_retornantes_anterior": prior_spend,
                    "variacao_gasto_retornantes": current_spend - prior_spend if count else None,
                    "frequencia_media_retornantes": current_frequency,
                    "frequencia_media_retornantes_anterior": prior_frequency,
                    "variacao_frequencia_retornantes": current_frequency - prior_frequency
                    if count
                    else None,
                }
            )
            for client, values in clients.iterrows():
                history.setdefault(client, []).append(
                    (start, float(values.gasto), int(values.compras))
                )
        rows.append(row)
    note(
        context,
        "Recorrência = clientes únicos presentes em mais de uma campanha, "
        "divididos por todos os clientes identificados no recorte. A identidade da campanha "
        "inclui shopping e identificadores disponíveis. As médias gerais podem variar por "
        "mudança de composição e não representam evolução dos mesmos indivíduos. "
        "A coorte retornante compara os mesmos clientes com sua campanha anterior observada "
        "de início estritamente anterior; gastos e frequência são totais por campanha, "
        "sem ajuste pela duração. Campanhas com mesmo início não têm ordem entre si; "
        "clientes cuja campanha anterior mais recente é ambígua são excluídos da coorte.",
    )
    if not chronology:
        note(
            context,
            "Sem início declarado único para cada campanha, não se infere cronologia "
            "nem evolução da coorte; apenas recorrência e totais por campanha são apresentados.",
        )
    return pd.DataFrame(rows)


def analyze(data, mode, context, options):
    """Analyze precleaned canonical purchase rows, returning aggregate results only."""
    note(
        context,
        "Gasto e frequência por cliente usam apenas compras com cliente identificado; "
        "faturamento e quantidade de compras gerais também incluem compras anônimas válidas.",
    )
    handlers = {
        "weekday": _weekday,
        "ticket_evolution": _ticket_evolution,
        "campaign_phases": _phases,
        "campaign_retention": _retention,
    }
    if mode not in handlers:
        raise ValueError(f"Modo temporal desconhecido: {mode}")
    return handlers[mode](data, context)
