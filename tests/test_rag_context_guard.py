"""RAG retrieval and L0 context guard tests (require OpenAI API + seeded chroma_db)."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT / "chroma_db"

requires_openai = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
requires_chroma = pytest.mark.skipif(
    not CHROMA_DIR.is_dir(),
    reason="chroma_db not seeded; run scripts/seed_rag_index.py",
)


def test_build_context_delimiters():
    from core.rag.context_builder import build_context

    prompt = build_context(
        system="You are a support bot.",
        user_query="What is the refund policy?",
        chunks=[{"text": "Refunds within 30 days.", "metadata": {"source": "refund_policy.txt"}}],
    )
    assert "<system>" in prompt and "</system>" in prompt
    assert "<user_query>" in prompt and "</user_query>" in prompt
    assert "<retrieved_documents>" in prompt and "</retrieved_documents>" in prompt
    assert "refund_policy.txt" in prompt
    assert "Refunds within 30 days." in prompt


@requires_openai
@requires_chroma
def test_retrieve_poisoned_index_includes_poisoned_chunk():
    import core.env_setup  # noqa: F401

    from core.rag import RAGConfig, RAGRetriever, is_poisoned_source

    config = RAGConfig.from_env()
    retriever = RAGRetriever(config, collection_name=config.collection_poisoned)
    chunks = retriever.retrieve("What is the refund policy?", top_k=5)

    assert len(chunks) >= 1
    sources = {c["metadata"].get("source") for c in chunks}
    assert any(is_poisoned_source(s) for s in sources), f"Expected poisoned source, got {sources}"


@requires_openai
@requires_chroma
def test_l0_block_rejects_poisoned_retrieval():
    import core.env_setup  # noqa: F401

    from core.rag import RAGConfig, RAGRetriever, scan_chunks

    config = RAGConfig.from_env()
    retriever = RAGRetriever(config, collection_name=config.collection_poisoned)
    chunks = retriever.retrieve("What is the refund policy?", top_k=5)

    result = scan_chunks(chunks, policy="block")
    assert result.status == "REJECTED"
    assert result.chunks == []
    assert any(d.malicious for d in result.details)


@requires_openai
@requires_chroma
def test_l0_strip_keeps_benign_removes_poisoned():
    import core.env_setup  # noqa: F401

    from core.rag import RAGConfig, RAGRetriever, is_poisoned_source, scan_chunks

    config = RAGConfig.from_env()
    retriever = RAGRetriever(config, collection_name=config.collection_poisoned)
    chunks = retriever.retrieve("What is the refund policy?", top_k=5)

    result = scan_chunks(chunks, policy="strip")
    assert result.status == "APPROVED"
    assert len(result.chunks) >= 1
    assert not any(is_poisoned_source(c["metadata"].get("source", "")) for c in result.chunks)
    assert any(not is_poisoned_source(c["metadata"].get("source", "")) for c in result.chunks)
