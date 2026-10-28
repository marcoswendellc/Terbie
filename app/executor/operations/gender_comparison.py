"""Compare purchasing indicators using clients, rather than receipts, as observations."""

import math

import pandas as pd
from scipy.stats import ttest_ind

from app.executor.numeric import numeric_series
from app.executor.operations.base import BaseOperation

MIN_CLIENTS = 20
METRICS = ("gasto_total", "ticket_por_cliente", "compras")


class GenderPurchaseComparisonOperation(BaseOperation):
    operation_type = "gender_purchase_comparison"

    def execute(self, dataframe, operation, context):
        data = dataframe.copy()
        for column in ("sk_cliente", "cd_compra"):
            data[column] = data[column].astype("string").str.strip().replace("", pd.NA)
        gender_codes = data.cd_sexo.astype("string").str.strip().str.upper()
        gender_codes = gender_codes.str.replace(r"^([01])\.0+$", r"\1", regex=True)
        data["genero"] = gender_codes.map({
            "F": "Feminino", "0": "Feminino", "M": "Masculino", "1": "Masculino",
        })
        data["vl_compra"] = numeric_series(data.vl_compra)
        valid_amount = data.vl_compra.map(lambda x: pd.notna(x) and math.isfinite(float(x)))
        invalid = data.cd_compra.isna() | ~valid_amount | data.genero.isna()
        genders = data.groupby("sk_cliente").genero.nunique(dropna=False)
        bad_clients = set(genders[genders != 1].index)
        purchase_conflicts = data.groupby("cd_compra")[["sk_cliente", "vl_compra", "genero"]]
        conflicting_ids = purchase_conflicts.nunique(dropna=False).gt(1).any(axis=1)
        invalid |= data.cd_compra.isin(conflicting_ids[conflicting_ids].index)
        bad_clients.update(data.loc[invalid, "sk_cliente"].dropna())
        excluded_clients = len(bad_clients)
        missing_client_rows = int(data.sk_cliente.isna().sum())
        clean = data[data.sk_cliente.notna() & ~data.sk_cliente.isin(bad_clients)]
        clean = clean.drop_duplicates("cd_compra")
        clients = clean.groupby(["genero", "sk_cliente"]).agg(
            gasto_total=("vl_compra", "sum"), compras=("cd_compra", "nunique"),
        ).reset_index()
        clients["ticket_por_cliente"] = clients.gasto_total / clients.compras
        groups = {gender: clients[clients.genero.eq(gender)]
                  for gender in ("Feminino", "Masculino")}
        rows = []
        for gender, group in groups.items():
            if group.empty:
                continue
            revenue, count = float(group.gasto_total.sum()), int(group.compras.sum())
            rows.append({
                "genero": gender, "clientes_unicos": len(group), "quantidade_compras": count,
                "faturamento": revenue, "ticket_medio_por_compra": revenue / count,
                "gasto_medio_por_cliente": float(group.gasto_total.mean()),
                "compras_por_cliente": float(group.compras.mean()),
            })
        tests = []
        for metric in METRICS:
            women, men = groups["Feminino"][metric], groups["Masculino"][metric]
            difference = float(men.mean() - women.mean()) if len(women) and len(men) else None
            reference = float(women.mean()) if len(women) else 0
            test = {
                "metric": metric, "difference": difference,
                "relative_difference": (
                    difference / reference if reference and difference is not None else None
                ),
                "p_value": None, "adjusted_p_value": None, "ci_low": None, "ci_high": None,
                "significant": False, "status": "insufficient_clients",
            }
            if min(len(women), len(men)) >= MIN_CLIENTS:
                if women.var() + men.var() > 0:
                    result = ttest_ind(men.to_numpy(), women.to_numpy(), equal_var=False)
                    interval = result.confidence_interval(confidence_level=0.95)
                    if all(math.isfinite(float(value)) for value in (
                        result.pvalue, interval.low, interval.high,
                    )):
                        test.update(p_value=float(result.pvalue), ci_low=float(interval.low),
                                    ci_high=float(interval.high), status="tested")
                    else:
                        test["status"] = "numerical_limit"
                else:
                    test["status"] = "no_variation"
            tests.append(test)
        # Holm's step-down adjustment over the three predeclared outcomes.
        tested = sorted((item for item in tests if item["p_value"] is not None),
                        key=lambda item: item["p_value"])
        previous = 0.0
        for index, item in enumerate(tested):
            adjusted = min(1.0, max(previous, (len(METRICS) - index) * item["p_value"]))
            item.update(adjusted_p_value=adjusted, significant=adjusted < 0.05)
            previous = adjusted
        context.metadata["gender_comparison"] = {
            "tests": tests, "minimum_clients": MIN_CLIENTS, "excluded_clients": excluded_clients,
            "missing_client_rows": missing_client_rows, "unit": "cliente",
            "method": "Welch bilateral; Holm; IC95% individuais",
            "scope": operation.parameters.get("scope", []),
        }
        return pd.DataFrame(rows)
