from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    campanha: str | None = None
    empreendimento: str | None = None
    loja: str | None = None
    segmento: str | None = None
    periodo_inicio: str | None = None
    periodo_fim: str | None = None
    metrica: str | None = None
    ultima_pergunta: str | None = None
    ultima_resposta: str | None = None
    filtros: dict[str, Any] = Field(default_factory=dict)
    entidades: dict[str, str] = Field(default_factory=dict)
    intencao: str | None = None
    dimensao: str | None = None


class ConversationTurn(BaseModel):
    question: str
    rewritten_question: str
    answer: str
    result_data: list[dict[str, Any]] = Field(default_factory=list)


class ConversationSession(BaseModel):
    session_id: str
    state: ConversationState = Field(default_factory=ConversationState)
    recent_turns: list[ConversationTurn] = Field(default_factory=list)
    summary: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextualQuestion(BaseModel):
    original_question: str
    rewritten_question: str
    summary: str
    state: ConversationState
    clarification: str | None = None
