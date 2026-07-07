from app.semantic.dictionary import SEMANTIC_DICTIONARY
from app.semantic.models import SemanticMetric


def _build_metrics() -> dict[str, SemanticMetric]:
    metrics: dict[str, SemanticMetric] = {}
    metric_definitions = SEMANTIC_DICTIONARY["metrics"]
    if not isinstance(metric_definitions, dict):
        return metrics

    for name, definition in metric_definitions.items():
        if not isinstance(name, str) or not isinstance(definition, dict):
            continue
        if definition.get("operation") is None:
            continue

        metrics[name] = SemanticMetric(
            name=name,
            operation=definition["operation"],
            column=definition.get("column"),
            synonyms=list(definition.get("synonyms", [])),
            equivalent_to=definition.get("equivalent_to"),
            expands_to=list(definition.get("expands_to", [])),
            ambiguity_policy=definition.get("ambiguity_policy"),
        )

    return metrics


SEMANTIC_METRICS: dict[str, SemanticMetric] = _build_metrics()
