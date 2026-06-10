"""Conditional LangSmith tracing for RAG (no LangChain)."""
import functools
import os
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def is_rag_trace_enabled() -> bool:
    """True when RAG spans should be emitted.

    Explicit RAG_TRACE_ENABLED=false always wins (bulk eval).
    Explicit true always enables. When unset, follows LANGSMITH_TRACING.
    """
    rag = os.getenv("RAG_TRACE_ENABLED", "").strip().lower()
    if rag in ("0", "false", "no"):
        return False
    if rag in ("1", "true", "yes"):
        return True
    return os.getenv("LANGSMITH_TRACING", "").strip().lower() in ("1", "true", "yes")


def maybe_traceable(func: F | None = None, **kwargs: Any) -> F | Callable[[F], F]:
    """Apply langsmith @traceable at call time when tracing is enabled."""

    def decorator(fn: F) -> F:
        traced_holder: dict[str, Any] = {"fn": None}

        @functools.wraps(fn)
        def wrapper(*args: Any, **kw: Any) -> Any:
            if not is_rag_trace_enabled():
                return fn(*args, **kw)
            if traced_holder["fn"] is None:
                try:
                    from langsmith import traceable

                    traced_holder["fn"] = traceable(**kwargs)(fn)
                except ImportError:
                    return fn(*args, **kw)
            return traced_holder["fn"](*args, **kw)

        return wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)
    return decorator


def set_run_metadata(**metadata: Any) -> None:
    """Attach metadata to the current LangSmith run (no-op when tracing is off)."""
    if not is_rag_trace_enabled():
        return
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is not None:
            run.metadata.update(metadata)
    except ImportError:
        pass
