"""L0 Context Guard: scan retrieved RAG chunks before they enter the LLM prompt."""
from dataclasses import dataclass, field
from typing import Literal

from core.judge_model import JudgeModel
from core.rag.guard_wrappers import full_scan
from core.rag.retriever import is_poisoned_source
from core.rag.tracing import maybe_traceable, set_run_metadata, set_run_outputs
from core.semantic_analyzer import SemanticAnalyzer

Policy = Literal["strip", "block"]


@dataclass
class ChunkScanResult:
    chunk: dict
    malicious: bool
    layer: str | None = None
    similarity: float = 0.0


@dataclass
class GuardResult:
    status: Literal["APPROVED", "REJECTED"]
    chunks: list[dict] = field(default_factory=list)
    details: list[ChunkScanResult] = field(default_factory=list)


@maybe_traceable(name="L0_scan_chunk", run_type="tool")
def scan_chunk(
    chunk: dict,
    analyzer: SemanticAnalyzer | None = None,
    judge: JudgeModel | None = None,
) -> ChunkScanResult:
    """Scan a single retrieved chunk with L1 → L2 (short-circuit)."""
    source = chunk.get("source") or chunk.get("metadata", {}).get("source", "unknown")
    poisoned = chunk.get("poisoned_source", is_poisoned_source(source))
    malicious, layer, similarity = full_scan(chunk["text"], analyzer, judge)

    set_run_metadata(
        chunk_id=chunk.get("id"),
        source=source,
        poisoned_source=poisoned,
        l0_malicious=malicious,
        l0_layer=layer,
        l0_similarity=round(similarity, 4),
    )
    set_run_outputs(
        chunk_id=chunk.get("id"),
        source=source,
        poisoned_source=poisoned,
        malicious=malicious,
        blocking_layer=layer,
        similarity=round(similarity, 4),
        text_preview=chunk["text"][:160] + ("…" if len(chunk["text"]) > 160 else ""),
    )

    return ChunkScanResult(
        chunk=chunk,
        malicious=malicious,
        layer=layer,
        similarity=similarity,
    )


@maybe_traceable(name="L0_context_guard", run_type="chain")
def scan_chunks(
    chunks: list[dict],
    policy: Policy = "block",
    analyzer: SemanticAnalyzer | None = None,
    judge: JudgeModel | None = None,
) -> GuardResult:
    """Scan all chunks. block → REJECT if any malicious; strip → drop malicious chunks."""
    details = [scan_chunk(chunk, analyzer, judge) for chunk in chunks]
    poisoned_ids = [
        d.chunk.get("id")
        for d in details
        if d.chunk.get("poisoned_source")
        or is_poisoned_source(d.chunk.get("metadata", {}).get("source", ""))
    ]
    summaries = [
        {
            "id": d.chunk.get("id"),
            "source": d.chunk.get("source") or d.chunk.get("metadata", {}).get("source"),
            "poisoned_source": d.chunk.get("poisoned_source")
            or is_poisoned_source(d.chunk.get("metadata", {}).get("source", "")),
            "malicious": d.malicious,
            "layer": d.layer,
            "similarity": round(d.similarity, 4),
        }
        for d in details
    ]

    if policy == "block":
        if any(d.malicious for d in details):
            set_run_metadata(
                policy=policy,
                chunk_count=len(chunks),
                malicious_count=sum(1 for d in details if d.malicious),
                poisoned_chunk_count=len(poisoned_ids),
                poisoned_chunk_ids=poisoned_ids,
                guard_status="REJECTED",
            )
            set_run_outputs(policy=policy, status="REJECTED", chunk_summaries=summaries)
            return GuardResult(status="REJECTED", chunks=[], details=details)

        set_run_metadata(
            policy=policy,
            chunk_count=len(chunks),
            malicious_count=0,
            poisoned_chunk_count=len(poisoned_ids),
            poisoned_chunk_ids=poisoned_ids,
            guard_status="APPROVED",
        )
        set_run_outputs(policy=policy, status="APPROVED", chunk_summaries=summaries)
        return GuardResult(status="APPROVED", chunks=chunks, details=details)

    safe = [d.chunk for d in details if not d.malicious]
    set_run_metadata(
        policy=policy,
        chunk_count=len(chunks),
        malicious_count=sum(1 for d in details if d.malicious),
        poisoned_chunk_count=len(poisoned_ids),
        poisoned_chunk_ids=poisoned_ids,
        guard_status="APPROVED",
        chunks_kept=len(safe),
    )
    set_run_outputs(
        policy=policy,
        status="APPROVED",
        chunks_kept=len(safe),
        chunk_summaries=summaries,
    )
    return GuardResult(status="APPROVED", chunks=safe, details=details)
