"""Evaluate Layer 3 output filter with span-level PII metrics."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.output_filter import OutputFilter

DATA_PATH = ROOT / "data" / "pii_eval.json"
RESULTS_DIR = ROOT / "results"


def span_metrics(samples: list[dict], output_filter: OutputFilter) -> dict:
    tp = fp = fn = 0
    latencies = []
    per_type: dict[str, dict] = {}

    for sample in samples:
        start = time.perf_counter()
        filtered = output_filter.filter_output(sample["text"])
        latencies.append((time.perf_counter() - start) * 1000)

        gt_spans = sample.get("spans", [])
        for span in gt_spans:
            stype = span["type"]
            per_type.setdefault(stype, {"tp": 0, "fn": 0})
            if span["value"] not in filtered:
                tp += 1
                per_type[stype]["tp"] += 1
            else:
                fn += 1
                per_type[stype]["fn"] += 1

        # False positives: unexpected mask tokens when no ground-truth span of that type
        mask_tokens = filtered.count("[MASKED_")
        expected_masks = len(gt_spans)
        if mask_tokens > expected_masks:
            fp += mask_tokens - expected_masks

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    type_metrics = {}
    for stype, counts in per_type.items():
        t_tp, t_fn = counts["tp"], counts["fn"]
        t_recall = t_tp / (t_tp + t_fn) if (t_tp + t_fn) else 0.0
        type_metrics[stype] = {"recall": round(t_recall, 4), "tp": t_tp, "fn": t_fn}

    return {
        "samples": len(samples),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        },
        "by_type": type_metrics,
        "target_f1_min": 0.90,
    }


def merge_into_eval_report(pii_metrics: dict):
    report_path = RESULTS_DIR / "eval_report.json"
    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
    else:
        report = {}
    report["layer3_pii"] = pii_metrics
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Evaluate output filter PII detection")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not DATA_PATH.exists():
        print(f"Missing {DATA_PATH}. Run generate_pii_eval.py first.")
        sys.exit(1)

    with open(DATA_PATH, encoding="utf-8") as f:
        samples = json.load(f)
    if args.limit:
        samples = samples[: args.limit]

    try:
        output_filter = OutputFilter()
    except OSError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    metrics = span_metrics(samples, output_filter)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "pii_eval_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    merge_into_eval_report(metrics)

    print(f"PII eval: P={metrics['precision']} R={metrics['recall']} F1={metrics['f1']}")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
