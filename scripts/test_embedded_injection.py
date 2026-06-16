"""Isolated L0 test for a single (possibly hidden) injection file.

Chunks one corpus file exactly like the indexer would, then runs each chunk
through the L0 context guard (L1 semantic -> L2 judge) and prints the verdict.
No Chroma retrieval involved — this measures detection on the file directly.

Usage:
    python scripts/test_embedded_injection.py \
        data/rag_corpus/poisoned/refund_policy_embedded.txt
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import core.env_setup  # noqa: F401, E402 — SSL + .env

from core.rag import RAGConfig
from core.rag.chunker import chunk_text
from core.rag.guard_wrappers import full_scan
from core.semantic_analyzer import SemanticAnalyzer
from core.judge_model import JudgeModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Isolated L0 scan of one corpus file.")
    parser.add_argument("path", help="Path to the .txt file to test")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: file not found: {path}")
        sys.exit(1)

    cfg = RAGConfig.from_env()
    text = path.read_text(encoding="utf-8")
    chunks = chunk_text(text, source=path.name, chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap)

    analyzer = SemanticAnalyzer()
    judge = JudgeModel()

    print(f"\nFile: {path.name}")
    print(f"Chunks: {len(chunks)}  (chunk_size={cfg.chunk_size}, overlap={cfg.chunk_overlap})")
    print(f"L1 threshold (SEMANTIC_THRESHOLD): {analyzer.threshold}\n")

    any_blocked = False
    for c in chunks:
        is_mal, layer, sim = full_scan(c.text, analyzer, judge)
        any_blocked = any_blocked or is_mal
        verdict = "BLOCKED" if is_mal else "passed "
        by = f"by L0:{layer}" if is_mal else "—"
        print(f"[chunk {c.chunk_index}] {verdict}  L1_sim={sim:.4f}  {by}")
        print(f"    preview: {c.text[:140].replace(chr(10), ' ')}...\n")

    print("=" * 60)
    if any_blocked:
        print("RESULT: L0 guard CAUGHT the file (at least one chunk flagged).")
    else:
        print("RESULT: L0 guard MISSED — file passed both L1 and L2. Injection is hidden well enough to evade.")


if __name__ == "__main__":
    main()
