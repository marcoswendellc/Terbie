from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class FollowUpSuggestion(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    required_columns: list[str] = Field(default_factory=list, max_length=30)

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


class AnalysisQuestion(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    question: str = Field(min_length=1, max_length=2000)

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


class AnalysisDecision(BaseModel):
    goal: str = ""
    assumptions: list[str] = Field(default_factory=list, max_length=5)
    analyses: list[AnalysisQuestion] = Field(default_factory=list, max_length=3)
    clarification: str | None = None

    model_config = ConfigDict(frozen=True)


class SuggestionResponse(BaseModel):
    suggestions: list[FollowUpSuggestion] = Field(default_factory=list, max_length=2)


class ConversationProvider(Protocol):
    def decide(self, context: dict[str, Any], *, timeout_ms: int) -> AnalysisDecision | None: ...

    def suggest(
        self,
        context: dict[str, Any],
        *,
        timeout_ms: int,
    ) -> list[FollowUpSuggestion]: ...
