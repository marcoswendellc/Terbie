from abc import ABC, abstractmethod

from app.reasoning.models import ReasoningContext, ReasoningResult


class BaseReasoningProvider(ABC):
    """Port for future reasoning providers such as Gemini, OpenAI, or local models."""

    @abstractmethod
    def generate_hypothesis(self, context: ReasoningContext) -> ReasoningResult:
        raise NotImplementedError

    def generate_execution_plan(self, context: ReasoningContext) -> ReasoningResult:
        raise NotImplementedError
