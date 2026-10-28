"""Deterministic presentation of client-level gender comparisons."""


def gender_comparison_answer(context, formatter):
    details = context.execution_metadata["gender_comparison"]
    tests = details["tests"]
    lines = ["Comparação entre mulheres e homens com compras registradas no recorte solicitado."]
    campaign = context.execution_metadata.get("resolved_entities", {}).get("nm_promocao")
    if campaign:
        lines.append(f"Campanha analisada: {campaign}.")
    for scope in details.get("scope", []):
        if scope.get("field") == "nm_empreendimento":
            lines.append(f"Shopping: {scope['value']}.")
        if scope.get("field") == "dt_registro_mos" and scope.get("operator") == "date_between":
            lines.append(f"Compras de {scope['value']} a {scope['end_value']}.")
    table = [
        "| Gênero | Clientes | Compras | Faturamento | Ticket por compra "
        "| Gasto por cliente | Compras por cliente |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in context.data:
        values = [
            row["genero"], formatter.integer(row["clientes_unicos"]),
            formatter.integer(row["quantidade_compras"]),
            *[formatter.value("faturamento", row[key]) for key in (
                "faturamento", "ticket_medio_por_compra", "gasto_medio_por_cliente",
            )],
            f"{row['compras_por_cliente']:.2f}".replace(".", ","),
        ]
        table.append("| " + " | ".join(values) + " |")
    lines.append("\n".join(table))
    tested = [item for item in tests if item["p_value"] is not None]
    if tested:
        if any(item["significant"] for item in tested):
            lines.append("Há evidência de diferença estatística nos indicadores destacados abaixo.")
        else:
            lines.append("Não foi detectada diferença estatisticamente significativa; "
                         "isso não comprova igualdade entre os grupos.")
        lines.append("Teste de Welch bilateral por cliente, nível de 5%, com correção de Holm "
                     "para três indicadores. Diferenças calculadas como homens menos mulheres.")
        labels = {"gasto_total": "Gasto total por cliente",
                  "ticket_por_cliente": "Ticket médio individual",
                  "compras": "Compras por cliente"}
        for item in tested:
            def value(number, metric=item["metric"]):
                return (f"{number:.2f}".replace(".", ",") if metric == "compras"
                        else formatter.value("faturamento", number))
            relative = (f" ({item['relative_difference'] * 100:+.2f}%)".replace(".", ",")
                        if item["relative_difference"] is not None else "")
            verdict = "diferença significativa" if item["significant"] else "sem significância"
            lines.append(
                f"{labels[item['metric']]}: diferença {value(item['difference'])}{relative}; "
                f"IC95% individual [{value(item['ci_low'])}; {value(item['ci_high'])}]; "
                f"p ajustado = {item['adjusted_p_value']:.4g}; {verdict}."
            )
        lines.append("Os intervalos de confiança são individuais, sem ajuste simultâneo. "
                     "A decisão de significância usa o p ajustado. O ticket médio individual "
                     "dá o mesmo peso a cada cliente; difere do ticket por compra da tabela.")
    if any(item["status"] == "insufficient_clients" for item in tests):
        lines.append("Apenas comparação descritiva: exigimos pelo menos 20 clientes válidos "
                     "em cada grupo como regra operacional conservadora para os testes.")
    if any(item["status"] in {"no_variation", "numerical_limit"} for item in tests):
        lines.append("Indicadores sem variabilidade suficiente ou com limite numérico "
                     "não receberam conclusão de significância.")
    lines.append(
        f"Excluídos: {details['excluded_clients']} clientes com gênero ausente, fora dos dois "
        f"grupos, conflitante ou registros inválidos; {details['missing_client_rows']} registros "
        "sem identificação de cliente. Compras repetidas foram deduplicadas."
    )
    lines.append("Esta é uma associação observada, sem demonstração de causalidade. "
                 "O resultado depende de independência entre clientes e do recorte de "
                 "shopping, campanha e período; diferenças de composição podem influenciá-lo. "
                 "Descreve compras registradas, não todos os visitantes. Significância "
                 "estatística não determina, sozinha, relevância para o negócio.")
    return "\n\n".join(lines)
