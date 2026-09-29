"""Run varied questions against an independent oracle from a local workbook.

python -m scripts.evaluate_business_questions [--live] [--limit 10]
--live uses configured model providers, but always uses the local workbook.
Reports contain aggregate answers only; credentials and source rows are never logged.
"""

import argparse
import json
import logging
import math
import random
import unicodedata
from pathlib import Path

import pandas as pd

from app.core import dependencies as deps
from app.core.config import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--start", type=int, default=0)
    args = parser.parse_args()
    provider_failures = {}

    class ProviderFailureCounter(logging.Handler):
        def emit(self, record):
            if record.name == "app.conversation.gemini" and record.args:
                name = str(record.args[0])
                provider_failures[name] = provider_failures.get(name, 0) + 1

    logging.disable(logging.NOTSET)
    logging.getLogger().handlers = [ProviderFailureCounter()]
    logging.getLogger().setLevel(logging.WARNING)
    settings = Settings() if args.live else Settings(_env_file=None)
    if args.live and (settings.reasoning_provider != "gemini" or not settings.gemini_api_key):
        raise SystemExit("Modelo Gemini não configurado; avaliação online não executada.")
    settings = settings.model_copy(
        update={
            "google_sheets_spreadsheet_id": "local-evaluation",
            "memory_backend": "memory",
            "data_cache_ttl_seconds": 0,
        }
    )
    deps.provide_settings = lambda: settings
    frame = pd.read_excel("Teste Terbie.xlsx", sheet_name="Planilha1")

    class LocalData:
        def read_google_spreadsheet_data(self, **kwargs):
            return {settings.default_table: frame.copy()}

    deps.provide_data_service = lambda: LocalData()
    engine = deps.provide_execution_service()
    model_activity = {"attempted": 0, "responses_received": 0}
    if args.live and engine._conversation_director:
        provider = engine._conversation_director._provider
        generate = provider._generate

        def observed_generate(*positional, **keywords):
            model_activity["attempted"] += 1
            result = generate(*positional, **keywords)
            model_activity["responses_received"] += int(result is not None)
            return result

        provider._generate = observed_generate
    knowledge = deps.provide_knowledge_service().get_context()
    # Oracle uses direct pandas, independently of Terbie's planner/executor.
    frame["vl_compra"] = pd.to_numeric(frame.vl_compra, errors="raise")
    dates = pd.to_datetime(frame.dt_registro_mos, format="mixed", errors="coerce")
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
    year_scope = starts.le("2026-12-31") & ends.ge("2026-01-01")
    campaign = "Promoção Mães E Namorados 2026"
    scope = frame.loc[
        year_scope & frame.nm_promocao.eq(campaign) & frame.nm_empreendimento.eq("Buriti Shopping")
    ].copy()
    scope["genero"] = (
        scope.cd_sexo.astype(str)
        .str.strip()
        .str.upper()
        .map({"0": "Feminino", "F": "Feminino", "1": "Masculino", "M": "Masculino", "O": "Outros"})
        .fillna("Não informado")
    )
    metrics = {
        "faturamento": ("vl_compra", "sum"),
        "quantidade_compras": ("cd_compra", "nunique"),
        "clientes_unicos": ("sk_cliente", "nunique"),
    }
    cases = []
    for phrase, metric in [
        ("faturamento", "faturamento"),
        ("quantidade de compras", "quantidade_compras"),
        ("clientes únicos", "clientes_unicos"),
    ]:
        for label, field in [
            ("segmento", "nm_segmento"),
            ("segmento (nm_segmento)", "nm_segmento"),
            ("gênero", "genero"),
            ("gênero (genero)", "genero"),
            ("loja", "nm_fantasa"),
            ("bairro", "bairro"),
        ]:
            expected = (
                scope.groupby(field, dropna=False).agg(**{metric: metrics[metric]}).reset_index()
            )
            question = f'Mostre {phrase} da "{campaign}" do Buriti Shopping por {label} em 2026?'
            cases.append((question, expected, [field], [metric]))
    random.Random(20260929).shuffle(cases)
    for question, metric, campaign_only in [
        (
            "bom dia terbie, faça um gráfico evolutivo da quantidade de notas "
            "cadastradas em 2026 por mês",
            "quantidade_compras",
            False,
        ),
        ("qual a evolução mensal do faturamento nas campanhas em 2026?", "faturamento", True),
        ("Mostre o faturamento por mês em 2026", "faturamento", False),
    ]:
        selected = dates.dt.year.eq(2026)
        if campaign_only:
            selected &= frame.cd_promocao.notna()
        monthly = frame.loc[selected].assign(mes=dates.loc[selected].dt.strftime("%Y-%m"))
        expected = monthly.groupby("mes").agg(**{metric: metrics[metric]}).reset_index()
        cases.append((question, expected, ["mes"], [metric]))
    ranked = (
        frame.loc[year_scope & frame.cd_promocao.notna()]
        .groupby(["nm_promocao", "nm_empreendimento"], dropna=False)
        .agg(faturamento=("vl_compra", "sum"))
        .reset_index()
        .sort_values("faturamento", ascending=False)
        .head(1)
    )
    for question in [
        "qual campanha apresentou maior faturamento em 2026?",
        "olá chat, bom dia! qual foi a campanha com melhor performance em 2026?",
    ]:
        cases.append((question, ranked, ["nm_promocao", "nm_empreendimento"], ["faturamento"]))
    # Exact detailed questions from the conversation, preserving all five indicators.
    for label, field in [("segmento (nm_segmento)", "nm_segmento"), ("gênero (genero)", "genero")]:
        expected = scope.groupby(field, dropna=False).agg(**metrics).reset_index()
        expected["ticket_medio_por_compra"] = expected.faturamento / expected.quantidade_compras
        expected["ticket_medio_por_cliente"] = expected.faturamento / expected.clientes_unicos
        question = (
            f"Qual foi o faturamento, a quantidade de compras, os clientes únicos, "
            f'o ticket médio por compra e o ticket médio por cliente da "{campaign}" '
            f"por {label} em 2026?"
        )
        cases.append((question, expected, [field], list(expected.columns[1:])))
    for label, field in [("segmento", "nm_segmento"), ("gênero", "genero")]:
        expected = scope.groupby(field, dropna=False).agg(**metrics).reset_index()
        expected["ticket_medio_por_compra"] = expected.faturamento / expected.quantidade_compras
        expected["ticket_medio_por_cliente"] = expected.faturamento / expected.clientes_unicos
        cases.append((f"E por {label}?", expected, [field], list(expected.columns[1:])))

    def normalize(value):
        return "".join(
            char
            for char in unicodedata.normalize("NFKD", str(value).casefold())
            if not unicodedata.combining(char)
        ).strip()

    for place, field, value in [
        ("goiânia", "localidade", "goiania"),
        ("aparecida de goiânia", "localidade", "aparecida de goiania"),
        ("GO", "uf", "go"),
        ("SP", "uf", "sp"),
        ("estado de SP", "uf", "sp"),
    ]:
        selected = frame.loc[frame[field].map(normalize).eq(value)]
        expected = pd.DataFrame(
            [{"ticket_medio_por_compra": selected.vl_compra.sum() / selected.cd_compra.nunique()}]
        )
        cases.append(
            (f"Qual o ticket médio de {place}?", expected, [], ["ticket_medio_por_compra"])
        )
    selected = frame.loc[frame.uf.map(normalize).eq("go")]
    cases.append(
        (
            "e do GO?",
            pd.DataFrame(
                [
                    {
                        "ticket_medio_por_compra": selected.vl_compra.sum()
                        / selected.cd_compra.nunique()
                    }
                ]
            ),
            [],
            ["ticket_medio_por_compra"],
        )
    )
    selected = frame.loc[
        dates.dt.year.eq(2026)
        & frame.bairro.notna()
        & ~frame.bairro.map(normalize).isin(["", "null", "none", "nan", "nao informado"])
    ]
    expected = (
        selected.groupby("bairro")
        .agg(quantidade_compras=("cd_compra", "nunique"))
        .reset_index()
        .sort_values("quantidade_compras", ascending=False)
        .head(1)
    )
    cases.append(
        (
            "qual bairro apresentou maior volume de notas cadastradas em 2026?",
            expected,
            ["bairro"],
            ["quantidade_compras"],
        )
    )
    selected = frame.loc[dates.dt.year.eq(2026) & dates.dt.month.eq(5)]
    expected = pd.DataFrame(
        [
            {
                "clientes_unicos": selected.sk_cliente.nunique(),
                "quantidade_compras": selected.cd_compra.nunique(),
            }
        ]
    )
    cases.append(
        (
            "qual o perfil dos clientes das compras em maio/26?",
            expected,
            [],
            ["clientes_unicos", "quantidade_compras"],
        )
    )
    cases = cases[args.start :]
    report = []
    for index, (question, expected, dimensions, indicators) in enumerate(cases[: args.limit]):
        try:
            response = engine.execute_question(
                question=question, knowledge_context=knowledge, session_id="business-evaluation"
            )

            def key(row, dimensions=dimensions):
                return tuple("<null>" if pd.isna(row.get(d)) else str(row[d]) for d in dimensions)

            actual = {key(row): row for row in response.data}
            correct = len(response.data) == len(expected)
            for row in expected.to_dict("records"):
                got = actual.get(key(row), {})
                correct &= all(
                    isinstance(got.get(m), int | float)
                    and math.isclose(got[m], row[m], rel_tol=1e-8, abs_tol=0.01)
                    for m in indicators
                )
            # A correct data array is insufficient: grouped values must be visible.
            for dimension in dimensions:
                correct &= all(
                    str(value) in response.answer
                    for value in expected[dimension]
                    if not pd.isna(value)
                )
            item = {
                "question": question,
                "passed": bool(correct),
                "expected_rows": len(expected),
                "actual_rows": len(response.data),
                "answer": response.answer,
                "warnings": response.warnings,
            }
        except Exception as exc:
            item = {"question": question, "passed": False, "error_type": type(exc).__name__}
        report.append(item)
        print(
            f"{index + 1}/{min(len(cases), args.limit)} "
            f"{'PASS' if item['passed'] else 'FAIL'} {question}",
            flush=True,
        )
    output = Path("evals") / (
        "business-live-results.json" if args.live else "business-local-results.json"
    )
    if args.start:
        output = output.with_stem(output.stem + f"-{args.start}")
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "mode": "configured-providers-local-data" if args.live else "offline",
                "model_activity": model_activity,
                "provider_failure_types": provider_failures,
                "source_rows": len(frame),
                "seed": 20260929,
                "passed": sum(item["passed"] for item in report),
                "total": len(report),
                "cases": report,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Report: {output}")
    verified = all(item["passed"] for item in report)
    if args.live and not model_activity["responses_received"]:
        print("Modelo externo não respondeu: resultados validam somente o fallback local.")
        verified = False
    raise SystemExit(0 if verified else 1)


if __name__ == "__main__":
    main()
