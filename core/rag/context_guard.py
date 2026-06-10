"""L0 Context Guard: scan retrieved RAG chunks before they enter the LLM prompt."""
from dataclasses import dataclass, field
from typing import Literal

from core.judge_model import JudgeModel
from core.rag.guard_wrappers import full_scan
from core.rag.tracing import maybe_traceable, set_run_metadata
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
    malicious, layer, similarity = full_scan(chunk["text"], analyzer, judge)
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
    set_run_metadata(
        policy=policy,
        chunk_count=len(chunks),
        malicious_count=sum(1 for d in details if d.malicious),
    )

    if policy == "block":
        if any(d.malicious for d in details):
            return GuardResult(status="REJECTED", chunks=[], details=details)
        return GuardResult(status="APPROVED", chunks=chunks, details=details)

    safe = [d.chunk for d in details if not d.malicious]
    return GuardResult(status="APPROVED", chunks=safe, details=details)
