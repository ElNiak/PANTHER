"""Structured log context using contextvars for PANTHER framework.

Provides a frozen LogContext dataclass that travels with the current
execution context via contextvars. The log_context() context manager
lets callers push/pop context fields without threading them through
every function signature.

Example:
    from panther.core.utils.log_context import log_context, get_log_context

    with log_context(experiment_id="exp-1", phase="init"):
        with log_context(test_id="test-42"):
            ctx = get_log_context()
            assert ctx.experiment_id == "exp-1"
            assert ctx.test_id == "test-42"
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class LogContext:
    """Immutable snapshot of the current structured-logging context.

    Fields correspond to the PANTHER execution hierarchy and are
    automatically injected into every JSONL log record by
    StructuredJsonFormatter.
    """

    experiment_id: Optional[str] = None
    test_id: Optional[str] = None
    service_id: Optional[str] = None
    phase: Optional[str] = None
    correlation_id: Optional[str] = None

    def with_updates(self, **kwargs: Optional[str]) -> "LogContext":
        """Return a new LogContext with selected fields overridden.

        Only non-None values in kwargs are applied; existing fields
        that are not mentioned are preserved.

        Args:
            **kwargs: Field name/value pairs to override.

        Returns:
            New LogContext with merged fields.
        """
        current = asdict(self)
        current.update({k: v for k, v in kwargs.items() if v is not None})
        return LogContext(**current)


_current_context: ContextVar[LogContext] = ContextVar(
    "panther_log_context", default=LogContext()
)


def get_log_context() -> LogContext:
    """Return the LogContext for the current execution context."""
    return _current_context.get()


@contextmanager
def log_context(**kwargs: Optional[str]):
    """Push a new LogContext layer; automatically pop on exit.

    Nesting merges fields: inner values override outer ones for the same
    key, while unmentioned keys are inherited.

    Args:
        **kwargs: LogContext field overrides (experiment_id, test_id, etc.).

    Yields:
        None. Use get_log_context() to read the current context.
    """
    old = _current_context.get()
    token = _current_context.set(old.with_updates(**kwargs))
    try:
        yield
    finally:
        _current_context.reset(token)
