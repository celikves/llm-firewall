"""Evaluate RAG L3 exfil output guard (separate from PII eval)."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.rag.output_guard import filter_exfil_output

DATA_PATH = ROOT / "data" / "exfil_eval.json"
RESULTS_DIR = ROOT / "results"


def evaluate(samples: list[dict]) -> dict:
    tp = fp = fn = 0
    latencies: list[float] = []
    per_type: dict[str, dict[str, int]] = {}

    for sample in samples:
        start = time.perf_counter()
        filtered = filter_exfil_output(sample["text"])
        latencies.append((time.perf_counter() - start) * 1000)

        targets = sample.get("targets", [])
        for target in targets:
            token = target["token"]
            value = target["value"]
            ttype = "url" if token == "[BLOCKED_URL]" else "exfil"
            per_type.setdefault(ttype, {"tp": 0, "fn": 0})

            if value not in filtered and token in filtered:
                tp += 1
                per_type[ttype]["tp"] += 1
            else:
                fn += 1
                per_type[ttype]["fn"] += 1

        expected_blocks = len(targets)
        actual_blocks = filtered.count("[BLOCKED_URL]") + filtered.count("[BLOCKED_EXFIL]")
        if actual_blocks > expected_blocks:
            fp += actual_blocks - expected_blocks

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    by_type = {}
    for ttype, counts in per_type.items():
        t_tp, t_fn = counts["tp"], counts["fn"]
        t_recall = t_tp / (t_tp + t_fn) if (t_tp + t_fn) else 0.0
        by_type[ttype] = {"recall": round(t_recall, 4), "tp": t_tp, "fn": t_fn}

    return {
        "samples": len(samples),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "latency_ms": {"mean": round(sum(latencies) / len(latencies), 2) if latencies else 0.0},
        "by_type": by_type,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG L3 exfil output filter.")
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    args = parser.parse_args()

    with open(args.data, encoding="utf-8") as f:
        samples = json.load(f)

    metrics = evaluate(samples)
    print(json.dumps(metrics, indent=2))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "exfil_eval_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
