"""Serialize RAG pipeline results for API / dashboard responses."""
from core.rag.context_guard import GuardResult
from core.rag.retriever import is_poisoned_source


def serialize_retrieved_chunks(guard: GuardResult | None, policy: str) -> list[dict]:
    if not guard:
        return []

    kept_ids = {c["id"] for c in guard.chunks}
    rows: list[dict] = []
    for detail in guard.details:
        chunk = detail.chunk
        source = chunk.get("metadata", {}).get("source", "unknown")
        poisoned = is_poisoned_source(source)
        kept = chunk["id"] in kept_ids
        if policy == "block" and guard.status == "REJECTED":
            kept = False

        rows.append(
            {
                "id": chunk["id"],
                "source": source,
                "score": chunk.get("score"),
                "poisoned_source": poisoned,
                "l0_malicious": detail.malicious,
                "l0_layer": detail.layer,
                "kept_in_prompt": kept,
                "stripped": poisoned or detail.malicious and not kept,
                "text_preview": chunk["text"][:240] + ("…" if len(chunk["text"]) > 240 else ""),
                "text": chunk["text"],
            }
        )
    return rows
