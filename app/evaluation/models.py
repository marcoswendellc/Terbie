from collections.abc import Callable

from pydantic import BaseModel, Field

from app.compiler.models import CompilerResponse


class EvaluationCase(BaseModel):
    question: str
    expected_intent: str
    expected_format: str | None = None
    expected_contexts: list[dict[str, str]] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)


def evaluate_case(
    case: EvaluationCase,
    compile_question: Callable[[str], CompilerResponse],
) -> EvaluationResult:
    response = compile_question(case.question)
    failures: list[str] = []
    if response.hypothesis.analysis_type != case.expected_intent:
        failures.append(f"intent={response.hypothesis.analysis_type!r}, esperado={case.expected_intent!r}")
    if case.expected_format is not None and response.hypothesis.presentation.format != case.expected_format:
        failures.append(f"format={response.hypothesis.presentation.format!r}, esperado={case.expected_format!r}")
    actual_contexts = [
        {"promotion": str(item.get("promotion")), "shopping": str(item.get("shopping"))}
        for item in response.hypothesis.comparison_entities
    ]
    if case.expected_contexts and actual_contexts != case.expected_contexts:
        failures.append(f"contexts={actual_contexts!r}, esperado={case.expected_contexts!r}")
    return EvaluationResult(passed=not failures, failures=failures)
