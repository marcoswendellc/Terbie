"""Read-only executive evaluation using configured providers and current source data."""

import argparse
import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter

import pandas as pd

from app.core import dependencies as deps


def parse_source_dates(series):
    def parse(value):
        text = str(value).strip()
        try:
            if len(text) >= 10 and text[4] == "-":
                return datetime.fromisoformat(text[:10])
            if len(text) == 8 and text.isdigit():
                return datetime.strptime(text, "%Y%m%d")
            if len(text) >= 10 and text[2] == "/":
                return datetime.strptime(text[:10], "%d/%m/%Y")
            if text.replace(".", "", 1).isdigit():
                return datetime(1899, 12, 30) + timedelta(days=float(text))
        except (ValueError, OverflowError):
            pass
        return pd.NaT

    lookup = {value: parse(value) for value in series.astype(str).unique()}
    return pd.to_datetime(series.astype(str).map(lookup), errors="coerce")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deterministic", action="store_true")
    args = parser.parse_args()
    logging.getLogger().handlers = [logging.NullHandler()]
    settings = deps.provide_settings().model_copy(
        update={"memory_backend": "memory", "data_cache_ttl_seconds": 3600}
    )
    deps.provide_settings = lambda: settings
    if args.deterministic:
        settings = settings.model_copy(update={"reasoning_provider": "mock"})
    engine = deps.provide_execution_service()
    frames = engine._load_dataframes()
    frame = frames[settings.default_table].copy()

    def currency(value):
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("R$", "").replace(" ", "")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        return float(text)

    frame["vl_compra"] = frame.vl_compra.map(currency)
    valid_campaign = frame.cd_promocao.notna() & ~frame.cd_promocao.astype(
        str
    ).str.strip().str.casefold().isin(["", "null", "none", "nan"])
    campaigns = frame.loc[valid_campaign].copy()
    dims = ["nm_promocao", "nm_empreendimento"]
    expected_campaigns = (
        campaigns.groupby(dims, dropna=False)
        .agg(
            faturamento=("vl_compra", "sum"),
            quantidade_compras=("cd_compra", "nunique"),
            clientes_unicos=("sk_cliente", "nunique"),
        )
        .reset_index()
    )
    expected_campaigns["ticket_medio_por_compra"] = (
        expected_campaigns.faturamento / expected_campaigns.quantidade_compras
    )
    expected_campaigns["ticket_medio_por_cliente"] = (
        expected_campaigns.faturamento / expected_campaigns.clientes_unicos
    )
    dates = parse_source_dates(frame.dt_registro_mos)
    monthly = frame.loc[dates.dt.year.eq(2026)].copy()
    monthly["mes"] = dates.loc[monthly.index].dt.strftime("%Y-%m")
    expected_monthly = monthly.groupby("mes").agg(faturamento=("vl_compra", "sum")).reset_index()
    starts = pd.to_datetime(
        frame.sk_dtinicio.astype(str).str.replace(r"\.0$", "", regex=True),
        format="%Y%m%d",
        errors="coerce",
    )
    ends = pd.to_datetime(
        frame.sk_dtfim.astype(str).str.replace(r"\.0$", "", regex=True),
        format="%Y%m%d",
        errors="coerce",
    )

    activity = {"attempted": 0, "received": 0}
    if engine._conversation_director:
        provider = engine._conversation_director._provider
        generate = provider._generate

        def observed(*args, **kwargs):
            activity["attempted"] += 1
            result = generate(*args, **kwargs)
            activity["received"] += int(result is not None)
            return result

        provider._generate = observed

    cases = [
        ("D01", "Quais campanhas tiveram o melhor desempenho?", "general", None),
        (
            "D02",
            "Mostre o faturamento por campanha, do maior para o menor, identificando o shopping.",
            "campaign",
            "faturamento",
        ),
        (
            "D03",
            "Quero comparar clientes únicos por campanha. Identifique o shopping e "
            "ordene do maior para o menor.",
            "campaign",
            "clientes_unicos",
        ),
        (
            "D04",
            "Mostre a quantidade de compras por campanha, do maior para o menor, com o shopping.",
            "campaign",
            "quantidade_compras",
        ),
        (
            "D05",
            "Qual o ticket médio por compra por campanha? Mostre também o shopping, do "
            "maior para o menor.",
            "campaign",
            "ticket_medio_por_compra",
        ),
        (
            "D06",
            "Compare a campanha de mães 2026 do Buriti Shopping com a campanha de mães "
            "2026 do Shopping Sul.",
            "comparison",
            None,
        ),
        ("D07", "Qual é o perfil dos participantes das campanhas?", "profile", None),
        (
            "D08",
            "Mostre o faturamento por mês em 2026. Quero entender a evolução ao longo do ano.",
            "monthly",
            "faturamento",
        ),
        ("D09", "Qual foi a campanha mais recente e em qual shopping aconteceu?", "recent", None),
        ("D10", "Liste as campanhas de 2025 no Buriti Shopping.", "listing", 2025),
        ("D11", "E em 2026?", "listing", 2026),
        (
            "D12",
            "Compare a campanha de pais com a campanha de mães do Buriti Shopping em 2025.",
            "comparison_year",
            None,
        ),
        (
            "D13",
            "Qual campanha teve o maior ROI? Considere o investimento de marketing e o "
            "retorno incremental.",
            "limits",
            None,
        ),
        (
            "D14",
            "Por que a campanha de Mães 2026 do Shopping Sul vendeu mais? Foi a mídia "
            "que causou esse resultado?",
            "causality",
            None,
        ),
        (
            "D15",
            "Qual foi o faturamento das campanhas do Shopping Inexistente XYZ em 2026?",
            "unknown",
            None,
        ),
    ]
    report = {
        "started_at": datetime.now().isoformat(),
        "mode": "local-deterministic-live-google-sheets"
        if args.deterministic
        else "local-current-code-configured-providers-live-google-sheets",
        "source_rows": len(frame),
        "shoppings": int(frame.nm_empreendimento.nunique()),
        "campaign_shopping_pairs": len(expected_campaigns),
        "model": settings.gemini_model,
        "director_activity": activity,
        "cases": [],
    }
    output = Path(
        "evals/director-evaluation-2026-09-30"
        + ("-deterministic" if args.deterministic else "")
        + ".json"
    )
    knowledge = deps.provide_knowledge_service().get_context()

    def check_table(actual, expected, keys, metric, ordered=True):
        lookup = {
            tuple(str(row[key]) for key in keys): float(row[metric])
            for row in expected.to_dict("records")
        }
        checks = {
            "identity_columns": all(all(key in row for key in keys) for row in actual),
            "complete_rows": len(actual) == len(lookup),
            "values": True,
            "descending": True,
        }
        seen = []
        for row in actual:
            key = tuple(str(row.get(col)) for col in keys)
            value = row.get(metric)
            checks["values"] &= (
                key in lookup
                and isinstance(value, (int, float))
                and math.isclose(value, lookup.get(key, 0), abs_tol=0.02)
            )
            if isinstance(value, (int, float)):
                seen.append(value)
        if ordered:
                checks["descending"] = all(a >= b for a, b in zip(seen, seen[1:], strict=False))
        return checks

    for case_id, question, kind, metric in cases:
        started = perf_counter()
        before = dict(activity)
        try:
            result = engine.execute_question(
                question=question,
                knowledge_context=knowledge,
                session_id="director-eval-years"
                if case_id in {"D10", "D11"}
                else f"director-eval-{case_id}",
            )
            payload = result.model_dump(mode="json")
            actual = result.data
            checks = {}
            expected = None
            if kind == "campaign":
                expected = expected_campaigns[dims + [metric]].sort_values(metric, ascending=False)
                checks = check_table(actual, expected, dims, metric)
            elif kind == "monthly":
                expected = expected_monthly
                checks = check_table(actual, expected, ["mes"], "faturamento", ordered=False)
                checks["chronological"] = [
                    row.get("mes") for row in actual
                ] == expected.mes.tolist()
            elif kind == "profile":
                expected = pd.DataFrame(
                    [
                        {
                            "clientes_unicos": campaigns.sk_cliente.nunique(),
                            "quantidade_compras": campaigns.cd_compra.nunique(),
                        }
                    ]
                )
                checks = {
                    "unique_customers": len(actual) == 1
                    and actual[0].get("clientes_unicos") == expected.iloc[0].clientes_unicos,
                    "purchase_count": len(actual) == 1
                    and actual[0].get("quantidade_compras") == expected.iloc[0].quantidade_compras,
                }
            elif kind == "listing":
                selected = frame.loc[
                    frame.nm_empreendimento.eq("Buriti Shopping")
                    & starts.le(f"{metric}-12-31")
                    & ends.ge(f"{metric}-01-01")
                ]
                expected = selected[dims + ["sk_dtinicio", "sk_dtfim"]].drop_duplicates()
                expected_names = set(expected.nm_promocao)
                checks = {
                    "campaigns": {row.get("nm_promocao") for row in actual} == expected_names,
                    "shopping": all(
                        row.get("nm_empreendimento") == "Buriti Shopping" for row in actual
                    ),
                    "count": len(actual) == len(expected),
                }
            elif kind == "comparison_year":
                expected = expected_campaigns.loc[
                    expected_campaigns.nm_empreendimento.eq("Buriti Shopping")
                    & expected_campaigns.nm_promocao.str.contains("2025")
                ]
            elif kind == "comparison":
                expected = expected_campaigns.loc[
                    expected_campaigns.nm_empreendimento.isin(["Buriti Shopping", "Shopping Sul"])
                    & expected_campaigns.nm_promocao.str.contains("Mães", case=False)
                ]
            elif kind == "general":
                expected = expected_campaigns
            elif kind == "recent":
                selected = frame.loc[starts.le(pd.Timestamp.today().normalize())]
                latest = starts.loc[selected.index].max()
                expected = selected.loc[
                    starts.loc[selected.index].eq(latest), dims + ["sk_dtinicio", "sk_dtfim"]
                ].drop_duplicates()
            report["cases"].append(
                {
                    "id": case_id,
                    "question": question,
                    "kind": kind,
                    "seconds": round(perf_counter() - started, 2),
                    "checks": checks,
                    "automatic_pass": all(checks.values()) if checks else None,
                    "expected": expected.to_dict("records") if expected is not None else None,
                    "result": payload,
                    "director_calls": {k: activity[k] - before[k] for k in activity},
                }
            )
            print(
                f"{case_id}: {report['cases'][-1]['automatic_pass']} / "
                f"{round(perf_counter() - started, 1)}s",
                flush=True,
            )
        except Exception as exc:
            report["cases"].append(
                {
                    "id": case_id,
                    "question": question,
                    "error_type": type(exc).__name__,
                    "seconds": round(perf_counter() - started, 2),
                }
            )
            print(f"{case_id}: error {type(exc).__name__}", flush=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
