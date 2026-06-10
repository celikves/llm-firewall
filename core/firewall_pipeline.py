"""Shared L1+L2 input verification (same logic as app.py /verify)."""
from dataclasses import dataclass
from typing import Literal

from core.judge_model import JudgeModel
from core.rag.guard_wrappers import judge_scan, semantic_scan
from core.semantic_analyzer import SemanticAnalyzer


@dataclass
class VerifyResult:
    status: Literal["APPROVED", "REJECTED"]
    layer: str | None = None
    similarity: float = 0.0


def verify(
    prompt: str,
    analyzer: SemanticAnalyzer | None = None,
    judge: JudgeModel | None = None,
) -> VerifyResult:
    """Run L1 semantic then L2 judge (short-circuit)."""
    is_attack, similarity = semantic_scan(prompt, analyzer)
    if is_attack:
        return VerifyResult(status="REJECTED", layer="semantic", similarity=similarity)

    if judge_scan(prompt, judge):
        return VerifyResult(status="REJECTED", layer="judge", similarity=similarity)

    return VerifyResult(status="APPROVED", similarity=similarity)
