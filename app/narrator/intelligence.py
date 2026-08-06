import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.narrator.models import NarrativeContext

logger = logging.getLogger(__name__)


class IntelligentNarrative(BaseModel):
    answer: str
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class BaseNarrativeProvider(ABC):
    @abstractmethod
    def generate(self, context: NarrativeContext) -> IntelligentNarrative | None:
        raise NotImplementedError


class GeminiNarrativeProvider(BaseNarrativeProvider):
    """Narrates calculated results without access to source tables."""

    def __init__(
        self,
        *,
        api_key: SecretStr | str | None,
        model: str,
        timeout_ms: int,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_ms = max(timeout_ms, 10000)
        self._client = client

    def generate(self, context: NarrativeContext) -> IntelligentNarrative | None:
        if self._api_key is None and self._client is None:
            return None

        try:
            from google.genai import types

            client = self._client or self._create_client()
            response = client.models.generate_content(
                model=self._model,
                contents=self._prompt(context),
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                    response_schema=IntelligentNarrative,
                ),
            )
            text = getattr(response, "text", None)
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Gemini narrative response is empty.")
            return IntelligentNarrative.model_validate_json(text)
        except Exception:
            logger.exception(
                "Gemini narrative generation failed; using deterministic narrative. "
                "model=%s",
                self._model,
            )
            return None

    def _prompt(self, context: NarrativeContext) -> str:
        safe_context = {
            "question": context.question,
            "intent": context.intent,
            "columns": context.columns,
            "rows_returned": context.rows_returned,
            "calculated_result": context.data[:50],
        }
        return (
            "Você é o narrador analítico do Terbie. Responda em português brasileiro "
            "com clareza e objetividade. Use exclusivamente os resultados calculados "
            "no JSON abaixo. Não invente causas, valores, tendências ou recomendações. "
            "Interprete livremente o pedido do usuário e escolha a apresentação mais "
            "adequada, sem depender de perguntas ou respostas predefinidas. Respeite "
            "explicitamente o formato solicitado pelo usuário. Quando ele pedir uma "
            "tabela, entregue uma tabela Markdown no campo answer. Quando pedir uma "
            "comparação entre entidades, apresente uma linha por indicador e colunas "
            "para cada entidade; inclua também variação absoluta e percentual, se os "
            "valores necessários estiverem presentes. Considere a primeira entidade "
            "como base e calcule a variação da segunda em relação à primeira. Se a "
            "base for zero, indique a variação percentual como não aplicável. "
            "Se a pergunta pedir análise, explique apenas relações sustentadas pelos "
            "números. Preserve nomes. Formate faturamento, receita, venda e ticket em "
            "reais (R$), percentuais com %, e contagens como inteiros. Retorne JSON "
            "compatível com o schema solicitado.\n\n"
            f"Contexto: {json.dumps(safe_context, ensure_ascii=False, default=str)}"
        )

    def _create_client(self) -> Any:
        from google import genai
        from google.genai import types

        api_key = (
            self._api_key.get_secret_value()
            if isinstance(self._api_key, SecretStr)
            else self._api_key
        )
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=self._timeout_ms),
        )
