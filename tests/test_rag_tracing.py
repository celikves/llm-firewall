"""Tests for conditional RAG LangSmith tracing."""
import os

import pytest

from core.rag.tracing import is_rag_trace_enabled, maybe_traceable


def test_is_rag_trace_enabled_false_by_default(monkeypatch):
    monkeypatch.delenv("RAG_TRACE_ENABLED", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert is_rag_trace_enabled() is False
    monkeypatch.setenv("RAG_TRACE_ENABLED", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert is_rag_trace_enabled() is False


def test_is_rag_trace_enabled_follows_langsmith_when_unset(monkeypatch):
    monkeypatch.delenv("RAG_TRACE_ENABLED", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert is_rag_trace_enabled() is True


def test_is_rag_trace_enabled_true(monkeypatch):
    monkeypatch.setenv("RAG_TRACE_ENABLED", "true")
    assert is_rag_trace_enabled() is True


def test_maybe_traceable_disabled_returns_same_function(monkeypatch):
    monkeypatch.setenv("RAG_TRACE_ENABLED", "false")

    @maybe_traceable(name="noop_span")
    def sample(x: int) -> int:
        return x + 1

    assert sample(2) == 3
    assert sample.__name__ == "sample"


def test_rag_query_import():
    from core.rag.pipeline import rag_query

    assert callable(rag_query)


def test_firewall_verify_import():
    from core.firewall_pipeline import verify

    assert callable(verify)


@pytest.mark.parametrize("value", ("1", "true", "yes", "TRUE"))
def test_is_rag_trace_enabled_truthy_values(monkeypatch, value):
    monkeypatch.setenv("RAG_TRACE_ENABLED", value)
    assert is_rag_trace_enabled() is True
