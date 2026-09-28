import logging
from collections.abc import Callable
from time import monotonic
from typing import Any

import pandas as pd

from app.conversation.budget import analytical_deadline
from app.conversation.models import (
    AnalysisDecision,
    AnalysisQuestion,
    ConversationProvider,
    FollowUpSuggestion,
)
from app.memory.models import ConversationSession
from app.narrator.models import ExecuteResponse
from app.semantic.temporal import TemporalSelection, resolve_temporal_reference

logger = logging.getLogger(__name__)


def schema_context(dataframes: dict[str, pd.DataFrame]) -> dict[str, dict[str, str]]:
    """Only structure, never source values or sample rows."""
    return {
        name: {str(column): str(dtype) for column, dtype in frame.dtypes.items()}
        for name, frame in dataframes.items()
    }


class ConversationDirector:
    def __init__(
        self,
        provider: ConversationProvider,
        *,
        max_analyses: int = 3,
        budget_seconds: float = 60,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._provider = provider
        self._max_analyses = min(max(max_analyses, 1), 3)
        self._budget = budget_seconds
        self._clock = clock

    def run(
        self,
        *,
        question: str,
        session: ConversationSession | None,
        schemas: dict[str, dict[str, str]],
        knowledge: dict[str, Any],
        execute: Callable[[str], ExecuteResponse],
        validate_suggestion: Callable[[str], bool] | None = None,
    ) -> ExecuteResponse | None:
        deadline = self._clock() + self._budget
        previous = session.recent_turns[-1].question if session and session.recent_turns else ""
        if session and session.recent_turns and TemporalSelection.parse(previous) is None:
            previous = session.recent_turns[-1].rewritten_question
        resolved = resolve_temporal_reference(question, previous) or question
        temporal = TemporalSelection.parse(resolved)
        context = {
            "question": question,
            "schemas": schemas,
            "knowledge": knowledge,
            "conversation": self._history(session),
        }
        try:
            decision = (
                AnalysisDecision(
                    goal="Identificar campanha por data",
                    assumptions=[temporal.assumption],
                    analyses=[AnalysisQuestion(title="Campanha por data", question=resolved)],
                )
                if temporal
                else self._provider.decide(context, timeout_ms=self._remaining(deadline))
            )
        except Exception:
            logger.exception("Conversational direction unavailable")
            return None
        if decision is None:
            return None
        if decision.clarification:
            return ExecuteResponse(
                question=question,
                answer=decision.clarification,
                data=[],
                metadata={"response_type": "clarification_required", "goal": decision.goal},
            )
        if not decision.analyses:
            return None
        answers: list[str] = []
        items: list[dict[str, Any]] = []
        warnings: list[str] = []
        completed: list[ExecuteResponse] = []
        if len(decision.analyses) > self._max_analyses:
            warnings.append("Parte da análise ficou pendente pelo limite de consultas deste turno.")
        for analysis in decision.analyses[: self._max_analyses]:
            if self._remaining(deadline) <= 0:
                warnings.append(
                    "O limite de tempo foi atingido; as análises restantes ficaram pendentes."
                )
                break
            try:
                with analytical_deadline(deadline, self._clock):
                    response = execute(analysis.question)
                verification = response.metadata.get("verification", {})
                checks = verification.get("checks", {})
                only_empty = checks.get("has_rows") is False and all(
                    value for name, value in checks.items() if name != "has_rows"
                )
                if verification.get("passed") is False and not only_empty:
                    raise ValueError("Unverified analytical result")
                if response.metadata.get("response_type") in {
                    "analysis_failed",
                    "clarification_required",
                    "out_of_scope",
                }:
                    answers.append(f"{analysis.title}\n{response.answer}")
                    items.append({"title": analysis.title, "status": "failed", "data": []})
                    warnings.extend(response.warnings)
                    continue
                completed.append(response)
                items.append({"title": analysis.title, "status": "success", "data": response.data})
                answers.append(f"{analysis.title}\n{response.answer}")
                warnings.extend(response.warnings)
            except Exception:
                logger.exception("Conversational analysis failed")
                message = f"{analysis.title}: não foi possível concluir esta análise."
                answers.append(message)
                warnings.append(message)
                items.append({"title": analysis.title, "status": "failed", "data": []})

        suggestions: list[FollowUpSuggestion] = []
        if completed and self._remaining(deadline) > 0:
            try:
                proposed = self._provider.suggest(
                    {
                        **context,
                        "analyses": [a.model_dump() for a in decision.analyses],
                        "results": [
                            {"title": item["title"], "data": item["data"][:50]}
                            for item in items
                            if item["status"] == "success"
                        ],
                    },
                    timeout_ms=self._remaining(deadline),
                )
                seen: set[str] = set()
                for suggestion in proposed:
                    if self._remaining(deadline) <= 0:
                        break
                    required = set(suggestion.required_columns)
                    if not required or not any(
                        required.issubset(columns) for columns in schemas.values()
                    ):
                        continue
                    if suggestion.question.casefold() in seen:
                        continue
                    if validate_suggestion and not validate_suggestion(suggestion.question):
                        continue
                    seen.add(suggestion.question.casefold())
                    suggestions.append(suggestion)
                    if len(suggestions) == 2:
                        break
            except Exception:
                logger.exception("Follow-up suggestions unavailable")

        single = len(items) == 1 and len(completed) == 1
        return ExecuteResponse(
            question=question,
            answer=(completed[0].answer if single else "\n\n".join(answers))
            or "Não consegui concluir a análise neste turno. Tente um recorte menor.",
            data=completed[0].data if single else items,
            assumptions=decision.assumptions,
            suggestions=suggestions,
            warnings=list(dict.fromkeys(warnings)),
            metadata={
                **(completed[0].metadata if single else {}),
                "response_type": "conversational_analysis" if completed else "analysis_failed",
                "goal": decision.goal,
                "analysis_questions": [a.question for a in decision.analyses[: len(items)]],
                "successful_analyses": len(completed),
                "failed_analyses": len(items) - len(completed),
                "pending_analyses": len(decision.analyses) - len(items),
            },
        )

    def _remaining(self, deadline: float) -> int:
        return max(0, int((deadline - self._clock()) * 1000))

    @staticmethod
    def _history(session: ConversationSession | None) -> dict[str, Any]:
        if session is None:
            return {}
        return {
            "goal": session.goal,
            "analysis_questions": session.analysis_questions,
            "suggestions": [item.model_dump() for item in session.suggestions],
            "recent_turns": [
                {
                    "question": turn.question,
                    "resolved_question": turn.rewritten_question,
                    "answer": turn.answer,
                    "result_data": turn.result_data[:20],
                }
                for turn in session.recent_turns
            ],
        }
