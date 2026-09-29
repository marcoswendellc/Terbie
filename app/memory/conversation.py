import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from app.context_resolution.context_resolver import ContextResolver
from app.conversation.models import FollowUpSuggestion
from app.memory.base import BaseMemory
from app.memory.models import (
    ContextualQuestion,
    ConversationSession,
    ConversationState,
    ConversationTurn,
)
from app.planner.models import ExecutionPlan, PlanOperation
from app.semantic.explicit_query import is_explicit_query
from app.semantic.temporal import TemporalSelection, resolve_temporal_reference


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
        previous = session.recent_turns[-1].question if session.recent_turns else ""
        if session.recent_turns and TemporalSelection.parse(previous) is None:
            previous = session.recent_turns[-1].rewritten_question
        temporal_reference = resolve_temporal_reference(question, previous)
        if temporal_reference:
            return ContextualQuestion(
                original_question=question,
                rewritten_question=temporal_reference,
                summary=self._conversation_context(session),
                state=state,
            )
        selected, clarification = self.resolve_suggestion(session=session, question=question)
        if selected or clarification:
            return ContextualQuestion(
                original_question=question,
                rewritten_question=selected or question,
                summary=self._conversation_context(session),
                state=state,
                clarification=clarification,
            )
        rewritten = question.strip()
        if (is_explicit_query(question) or ContextResolver().explicit_grouping(question)) and (
            normalized.startswith("e ")
            or re.search(r"\b(nessa|dessa|essa|nesse|desse)\b", normalized)
        ):
            if not self._has_metric(normalized) and session.recent_turns:
                prior_rows = session.recent_turns[-1].result_data
                labels = {
                    "faturamento": "faturamento",
                    "quantidade_compras": "quantidade de compras",
                    "clientes_unicos": "clientes únicos",
                    "ticket_medio_por_compra": "ticket médio por compra",
                    "ticket_medio_por_cliente": "ticket médio por cliente",
                }
                metrics = [
                    labels[key] for key in (prior_rows[0] if prior_rows else {}) if key in labels
                ]
                if metrics:
                    rewritten += "; indicadores: " + ", ".join(metrics)
            if "campanha" in normalized and not state.campanha:
                return ContextualQuestion(
                    original_question=question,
                    rewritten_question=question,
                    summary=self._conversation_context(session),
                    state=state,
                    clarification="Qual campanha você deseja detalhar?",
                )
            for key, label in [("campanha", "campanha"), ("empreendimento", "shopping")]:
                value = getattr(state, key)
                explicit_name = re.search(r"\b" + label + r'\s+(?!em\b|por\b)[\w"“]', normalized)
                if value and not explicit_name:
                    rewritten += f'; considerando {label} = "{value}"'
            if state.periodo_inicio and not re.search(r"\b(?:19|20)\d{2}\b", normalized):
                rewritten += f" em {state.periodo_inicio}"
            return ContextualQuestion(
                original_question=question,
                rewritten_question=rewritten,
                summary=self._conversation_context(session),
                state=state,
            )
        unresolved: list[str] = []

        ranked_reference = self._resolve_ranked_reference(
            question=question,
            normalized=normalized,
            session=session,
        )
        if ranked_reference is not None:
            rewritten = ranked_reference
            normalized = self._normalize(rewritten)

        # Corrections such as "quero saber a melhor" refer to the previous
        # analytical question, not to the aggregate shown in the last answer.
        # Reusing that question also avoids turning the previous winner into a
        # filter for the follow-up query.
        if self._is_result_correction(normalized) and state.ultima_pergunta:
            rewritten = state.ultima_pergunta
            return ContextualQuestion(
                original_question=question,
                rewritten_question=rewritten,
                summary=self._conversation_context(session),
                state=state,
            )

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
            summary=self._conversation_context(session),
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
        suggestions: list[FollowUpSuggestion] | None = None,
        analysis_questions: list[str] | None = None,
        goal: str = "",
        execution_metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        session = self.get(session_id)
        if plan is None and execution_metadata:
            trace = execution_metadata.get("operation_trace", [])
            plan = ExecutionPlan(
                operations=[
                    PlanOperation(
                        type="filter",
                        field=item.get("field"),
                        parameters={
                            "operator": item.get("operator", "equals"),
                            "value": item.get("resolved_value") or item.get("requested_value"),
                        },
                    )
                    for item in trace
                    if item.get("operation") == "filter"
                ]
            )
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
                result_data=[dict(row) for row in (data or [])[:50] if isinstance(row, dict)],
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
            goal=goal,
            analysis_questions=analysis_questions or [context.rewritten_question],
            suggestions=(suggestions or [])[:2],
            updated_at=datetime.now(UTC),
        )
        self._store.save(session_id, saved.model_dump(mode="json"))
        return saved

    def resolve_suggestion(
        self,
        *,
        session: ConversationSession,
        question: str,
    ) -> tuple[str | None, str | None]:
        """Resolve short choices only; explicit new filters belong to the planner."""
        if not session.suggestions:
            return None, None
        normalized = self._normalize(question).strip(" .!?;")
        ordinals = {"1": 0, "a primeira": 0, "primeira": 0, "2": 1, "a segunda": 1, "segunda": 1}
        if normalized in ordinals:
            index = ordinals[normalized]
            if index < len(session.suggestions):
                return session.suggestions[index].question, None
            return None, "Essa opção não está disponível. Qual aprofundamento você prefere?"
        if normalized in {"sim", "pode", "pode sim", "continue", "quero"}:
            if len(session.suggestions) == 1:
                return session.suggestions[0].question, None
            return None, "Qual aprofundamento você prefere: " + " ou ".join(
                item.label for item in session.suggestions
            ) + "?"
        stopwords = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "por"}
        tokens = set(normalized.split()) - stopwords
        matches = [
            item
            for item in session.suggestions
            if tokens and tokens.issubset(set(self._normalize(item.label).split()) - stopwords)
        ]
        if len(matches) == 1:
            return matches[0].question, None
        if len(matches) > 1:
            return None, "Qual destas opções: " + " ou ".join(item.label for item in matches) + "?"
        return None, None

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

    def _is_result_correction(self, normalized: str) -> bool:
        return bool(
            re.fullmatch(
                r"(?:eu\s+)?(?:quero|queria)\s+saber\s+(?:qual\s+)?"
                r"(?:foi\s+)?(?:a|o)\s+(?:melhor|maior)",
                normalized,
            )
            or re.fullmatch(r"(?:so\s+)?(?:a|o)\s+(?:melhor|maior)", normalized)
        )

    def _has_metric(self, normalized: str) -> bool:
        return any(
            term in normalized for term in ("venda", "faturamento", "ticket", "compra", "cliente")
        )

    def _conversation_context(self, session: ConversationSession) -> str:
        parts = [session.summary.strip()] if session.summary.strip() else []
        for turn in session.recent_turns:
            parts.append(f"Usuário: {turn.question}\nTerbie: {turn.answer}")
            if turn.result_data:
                parts.append(
                    "Resultado estruturado: "
                    + json.dumps(turn.result_data, ensure_ascii=False, default=str)
                )
        return "\n\n".join(parts)[-6000:]

    def _resolve_ranked_reference(
        self,
        *,
        question: str,
        normalized: str,
        session: ConversationSession,
    ) -> str | None:
        field_by_label = {
            "campanha": "nm_promocao",
            "promocao": "nm_promocao",
            "loja": "nm_fantasa",
            "segmento": "nm_segmento",
            "shopping": "nm_empreendimento",
            "empreendimento": "nm_empreendimento",
        }
        match = re.search(
            r"\b(campanha|promocao|loja|segmento|shopping|empreendimento)\s+(\d+)\b",
            normalized,
        )
        if match is None:
            return None

        label, raw_position = match.groups()
        position = int(raw_position)
        field = field_by_label[label]
        for turn in reversed(session.recent_turns):
            if position < 1 or position > len(turn.result_data):
                continue
            row = turn.result_data[position - 1]
            value = str(row.get(field) or "").strip()
            if not value:
                continue
            rewritten = re.sub(
                rf"\b{re.escape(label)}\s+{raw_position}\b",
                f"{label} {value}",
                question,
                count=1,
                flags=re.IGNORECASE,
            )
            shopping = str(row.get("nm_empreendimento") or "").strip()
            if shopping and field != "nm_empreendimento":
                rewritten += f"; referência do resultado anterior no shopping {shopping}"
            return rewritten
        return None

    def _normalize(self, text: str) -> str:
        value = "".join(
            c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
        )
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()
