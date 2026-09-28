from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_budget: ContextVar[tuple[float, Callable[[], float]] | None] = ContextVar(
    "analytical_turn_deadline",
    default=None,
)


@contextmanager
def analytical_deadline(deadline: float, clock: Callable[[], float]) -> Iterator[None]:
    token = _budget.set((deadline, clock))
    try:
        yield
    finally:
        _budget.reset(token)


def remaining_timeout(default_ms: int) -> int:
    budget = _budget.get()
    if budget is None:
        return default_ms
    deadline, clock = budget
    remaining = int((deadline - clock()) * 1000)
    if remaining <= 0:
        raise TimeoutError("Analytical turn budget exhausted")
    return min(default_ms, remaining)
