"""Thin wrappers around L1 SemanticAnalyzer and L2 JudgeModel for L0 context scanning."""
from core.judge_model import JudgeModel
from core.rag.tracing import maybe_traceable
from core.semantic_analyzer import SemanticAnalyzer


@maybe_traceable(name="L1_semantic", run_type="tool")
def semantic_scan(text: str, analyzer: SemanticAnalyzer | None = None) -> tuple[bool, float]:
    """Return (is_attack, max_similarity) using Layer 1."""
    layer = analyzer or SemanticAnalyzer()
    return layer.analyze(text)


@maybe_traceable(name="L2_judge", run_type="llm")
def judge_scan(text: str, judge: JudgeModel | None = None) -> bool:
    """Return True if Layer 2 flags the text as MALICIOUS."""
    layer = judge or JudgeModel()
    return layer.analyze(text)


def full_scan(
    text: str,
    analyzer: SemanticAnalyzer | None = None,
    judge: JudgeModel | None = None,
) -> tuple[bool, str | None, float]:
    """Run L1 then L2 (short-circuit). Return (is_malicious, blocking_layer, similarity)."""
    is_attack, similarity = semantic_scan(text, analyzer)
    if is_attack:
        return True, "semantic", similarity
    if judge_scan(text, judge):
        return True, "judge", similarity
    return False, None, similarity
