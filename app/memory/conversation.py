import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from app.memory.base import BaseMemory
from app.memory.models import (
    ContextualQuestion,
    ConversationSession,
    ConversationState,
    ConversationTurn,
)


class ConversationMemoryService:
    FIELD_TO_STATE = {
        "nm_promocao": "campanha",
        "nm_empreendimento": "empreendimento",
        "nm_fantasa": "loja",
        "nm_segmento": "segmento",
    }
    LABELS = {
        "campanha": "campanha",
        "empreendimento": "shopping",
        "loja": "loja",
        "segmento": "segmento",
    }
    REFERENCES = {
        "campanha": (r"\bnessa campanha\b", r"\bessa campanha\b"),
        "empreendimento": (r"\bnesse shopping\b", r"\besse shopping\b"),
        "loja": (r"\bnessa loja\b", r"\bessa loja\b"),
        "periodo": (r"\bnesse periodo\b",),
    }

    def __init__(self, store: BaseMemory, *, recent_limit: int = 4) -> None:
        self._store = store
        self._recent_limit = recent_limit

    def get(self, session_id: str) -> ConversationSession:
        saved = self._store.load(session_id)
        return (
            ConversationSession.model_validate(saved)
            if saved
            else ConversationSession(session_id=session_id)
        )

    def contextualize(self, *, session_id: str, question: str) -> ContextualQuestion:
        session = self.get(session_id)
        state = session.state
        normalized = self._normalize(question)
        rewritten = question.strip()
        unresolved: list[str] = []

        for key, patterns in self.REFERENCES.items():
            if not any(re.search(pattern, normalized) for pattern in patterns):
                continue
            value = self._period_value(state) if key == "periodo" else getattr(state, key)
            if value is None:
                unresolved.append(key)
                continue
            label = "período" if key == "periodo" else self.LABELS[key]
            rewritten += f"; considerando {label} = {value}"

        if re.search(r"\b(ela|dele|dela)\b", normalized):
            antecedent = self._pronoun_antecedent(state)
            if antecedent is None:
                unresolved.append("referência")
            else:
                key, value = antecedent
                rewritten += f"; considerando {self.LABELS[key]} = {value}"

        if "nesses dados" in normalized and not any(getattr(state, key) for key in self.LABELS):
            unresolved.append("dados anteriores")

        explicit = self._explicit_mentions(question)
        referenced_keys = self._referenced_keys(normalized)
        is_contextual = (
            bool(referenced_keys)
            or "nesses dados" in normalized
            or bool(re.search(r"\b(ela|dele|dela)\b", normalized))
        )
        # A terse follow-up inherits the analytical target, but explicit filters win.
        if self._is_elliptical(normalized):
            if state.dimensao:
                rewritten += f"; analisar por {self.LABELS.get(state.dimensao, state.dimensao)}"
            if state.metrica and not self._has_metric(normalized):
                rewritten += f"; métrica = {state.metrica}"
            if state.intencao:
                rewritten += f"; intenção = {state.intencao}"

        for key, value in state.model_dump().items():
            if key not in self.LABELS or not value or key in explicit or key in referenced_keys:
                continue
            # Carry filters only for a genuinely contextual/elliptical question.
            if self._is_elliptical(normalized) or is_contextual:
                rewritten += f"; considerando {self.LABELS[key]} = {value}"

        clarification = None
        if unresolved:
            names = ", ".join(dict.fromkeys(unresolved))
            clarification = (
                f"Não consegui identificar com segurança a referência a {names}. Pode especificar?"
            )
        return ContextualQuestion(
            original_question=question,
            rewritten_question=rewritten,
            summary=session.summary,
            state=state,
            clarification=clarification,
        )

    def record(
        self,
        *,
        session_id: str,
        context: ContextualQuestion,
        answer: str,
        plan: Any | None = None,
        data: list[dict[str, Any]] | None = None,
    ) -> ConversationSession:
        session = self.get(session_id)
        updates: dict[str, Any] = {
            "ultima_pergunta": context.original_question,
            "ultima_resposta": answer,
        }
        if plan is not None:
            updates["intencao"] = getattr(plan, "intent", None) or session.state.intencao
            metrics = getattr(plan, "metrics", [])
            entities = getattr(plan, "entities", [])
            if metrics:
                updates["metrica"] = metrics[0].name
            if entities:
                updates["dimensao"] = entities[0].name
            filters = dict(session.state.filtros)
            for operation in getattr(plan, "operations", []):
                if operation.type != "filter":
                    continue
                value = operation.parameters.get("value")
                if operation.field in {"sk_dtinicio", "dt_inicio"} and value is not None:
                    updates["periodo_inicio"] = str(value)
                    end_value = operation.parameters.get("end_value")
                    if end_value is not None:
                        updates["periodo_fim"] = str(end_value)
                    continue
                if operation.field not in self.FIELD_TO_STATE:
                    continue
                if value is not None:
                    key = self.FIELD_TO_STATE[operation.field]
                    updates[key] = str(value)
                    filters[operation.field] = value
            updates["filtros"] = filters

        if data:
            first = data[0]
            if isinstance(first, dict):
                entities = dict(session.state.entidades)
                for field, key in self.FIELD_TO_STATE.items():
                    value = first.get(field)
                    if value is not None:
                        updates[key] = str(value)
                        entities[field] = str(value)
                updates["entidades"] = entities

        new_state = session.state.model_copy(
            update={k: v for k, v in updates.items() if v is not None}
        )
        turns = [
            *session.recent_turns,
            ConversationTurn(
                question=context.original_question,
                rewritten_question=context.rewritten_question,
                answer=answer,
            ),
        ]
        overflow = turns[: -self._recent_limit]
        recent = turns[-self._recent_limit :]
        summary = session.summary
        if overflow:
            additions = " ".join(f"Usuário: {t.question} Terbie: {t.answer}" for t in overflow)
            summary = f"{summary} {additions}".strip()[-1500:]
        saved = ConversationSession(
            session_id=session_id,
            state=new_state,
            recent_turns=recent,
            summary=summary,
            updated_at=datetime.now(UTC),
        )
        self._store.save(session_id, saved.model_dump(mode="json"))
        return saved

    def _explicit_mentions(self, question: str) -> set[str]:
        normalized = self._normalize(question)
        found = set()
        patterns = {
            "campanha": r"\b(campanha|promocao)\s+[a-z0-9]",
            "empreendimento": r"\b(no|na|do|da)\s+(shopping\s+)?[a-z0-9]",
            "loja": r"\bloja\s+[a-z0-9]",
            "segmento": r"\bsegmento\s+[a-z0-9]",
        }
        for key, pattern in patterns.items():
            if re.search(pattern, normalized):
                found.add(key)
        return found

    def _referenced_keys(self, normalized: str) -> set[str]:
        return {
            key
            for key, patterns in self.REFERENCES.items()
            if any(re.search(p, normalized) for p in patterns)
        }

    def _pronoun_antecedent(self, state: ConversationState) -> tuple[str, str] | None:
        for key in ("empreendimento", "campanha", "loja", "segmento"):
            value = getattr(state, key)
            if value:
                return key, value
        return None

    def _period_value(self, state: ConversationState) -> str | None:
        if state.periodo_inicio and state.periodo_fim:
            return f"{state.periodo_inicio} a {state.periodo_fim}"
        return state.periodo_inicio or state.periodo_fim

    def _is_elliptical(self, normalized: str) -> bool:
        return normalized.startswith("e ") or bool(
            re.fullmatch(r"(e )?(no|na|do|da) .+", normalized)
        )

    def _has_metric(self, normalized: str) -> bool:
        return any(
            term in normalized for term in ("venda", "faturamento", "ticket", "compra", "cliente")
        )

    def _normalize(self, text: str) -> str:
        value = "".join(
            c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
        )
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()
