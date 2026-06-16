"""Statistical analysis: bootstrap CI, McNemar tests, category breakdown."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "results"
PREDICTIONS_PATH = RESULTS_DIR / "eval_predictions.json"
DATA_DIR = ROOT / "data"


def mcnemar_test(y_true: list[int], pred_a: list[int], pred_b: list[int]) -> dict:
    """McNemar test for paired classifier comparison."""
    b = sum(1 for yt, a, b_ in zip(y_true, pred_a, pred_b) if a == yt and b_ != yt)
    c = sum(1 for yt, a, b_ in zip(y_true, pred_a, pred_b) if a != yt and b_ == yt)
    if b + c == 0:
        return {"b": b, "c": c, "chi2": 0.0, "p_value": 1.0, "significant_005": False}
    chi2_stat = (abs(b - c) - 1) ** 2 / (b + c)
    p_value = 1 - chi2.cdf(chi2_stat, df=1)
    return {
        "b": b,
        "c": c,
        "chi2": round(float(chi2_stat), 4),
        "p_value": round(float(p_value), 6),
        "significant_005": bool(float(p_value) < 0.05),
    }


def bootstrap_ci(
    y_true: list[int],
    y_pred: list[int],
    metric: str = "f1",
    n_iterations: int = 1000,
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    values = []
    for _ in range(n_iterations):
        idx = rng.integers(0, n, n)
        yt = [y_true[i] for i in idx]
        yp = [y_pred[i] for i in idx]
        tp = sum(1 for a, b in zip(yt, yp) if a == 1 and b == 1)
        tn = sum(1 for a, b in zip(yt, yp) if a == 0 and b == 0)
        fp = sum(1 for a, b in zip(yt, yp) if a == 0 and b == 1)
        fn = sum(1 for a, b in zip(yt, yp) if a == 1 and b == 0)
        if metric == "f1":
            p = tp / (tp + fp) if (tp + fp) else 0.0
            r = tp / (tp + fn) if (tp + fn) else 0.0
            val = 2 * p * r / (p + r) if (p + r) else 0.0
        elif metric == "fp_rate":
            benign = fp + tn
            val = fp / benign if benign else 0.0
        else:
            val = (tp + tn) / n
        values.append(val)
    values = np.array(values)
    return {
        "mean": round(float(np.mean(values)), 4),
        "ci_lower": round(float(np.percentile(values, 2.5)), 4),
        "ci_upper": round(float(np.percentile(values, 97.5)), 4),
        "iterations": n_iterations,
    }


def category_breakdown(dataset: list[dict], y_pred: list[int]) -> dict:
    by_cat: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    for row, pred in zip(dataset, y_pred):
        cat = row.get("category", "unknown")
        yt = 1 if row["label"] == "malicious" else 0
        if yt == 1 and pred == 1:
            by_cat[cat]["tp"] += 1
        elif yt == 1 and pred == 0:
            by_cat[cat]["fn"] += 1
        elif yt == 0 and pred == 1:
            by_cat[cat]["fp"] += 1
        else:
            by_cat[cat]["tn"] += 1

    results = {}
    for cat, counts in sorted(by_cat.items()):
        tp, fn, fp, tn = counts["tp"], counts["fn"], counts["fp"], counts["tn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        results[cat] = {
            "samples": tp + fn + fp + tn,
            "f1": round(f1, 4),
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            **counts,
        }
    return results


def save_category_plot(breakdown: dict, mode: str, output: Path):
    cats = [c for c in breakdown if c not in ("benign", "benign_edge")]
    if not cats:
        cats = list(breakdown.keys())
    f1_vals = [breakdown[c]["f1"] for c in cats]

    plt.figure(figsize=(10, 5))
    plt.bar(cats, f1_vals, color="steelblue")
    plt.xticks(rotation=30, ha="right")
    plt.ylim(0, 1.05)
    plt.ylabel("F1 Score")
    plt.title(f"Category Breakdown — {mode} (eval_unseen malicious)")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def load_split_dataset(split: str) -> list[dict]:
    if split == "combined":
        with open(DATA_DIR / "eval_dataset.json", encoding="utf-8") as f:
            return json.load(f)
    malicious = json.loads((DATA_DIR / f"{split}.json").read_text(encoding="utf-8"))
    benign = json.loads((DATA_DIR / "eval_benign.json").read_text(encoding="utf-8"))
    return malicious + benign


def analyze_split(predictions: dict, split: str) -> dict:
    split_data = predictions["splits"][split]
    dataset = load_split_dataset(split)
    if len(dataset) != split_data["samples"]:
        dataset = dataset[: split_data["samples"]]

    analysis = {"samples": split_data["samples"], "modes": {}}
    for mode, mode_data in split_data["modes"].items():
        yt = mode_data["predictions"]["y_true"]
        yp = mode_data["predictions"]["y_pred"]
        analysis["modes"][mode] = {
            "bootstrap_f1": bootstrap_ci(yt, yp, "f1"),
            "bootstrap_fp_rate": bootstrap_ci(yt, yp, "fp_rate"),
        }
        if split in ("eval_unseen", "eval_seen", "combined"):
            mal_indices = [i for i, r in enumerate(dataset) if r["label"] == "malicious"]
            mal_rows = [dataset[i] for i in mal_indices]
            mal_pred = [yp[i] for i in mal_indices]
            if mal_rows:
                analysis["modes"][mode]["category_breakdown"] = category_breakdown(mal_rows, mal_pred)

    comparisons = {}
    if "keyword" in split_data["modes"] and "semantic" in split_data["modes"]:
        yt = split_data["modes"]["keyword"]["predictions"]["y_true"]
        comparisons["keyword_vs_semantic_h1"] = mcnemar_test(
            yt,
            split_data["modes"]["keyword"]["predictions"]["y_pred"],
            split_data["modes"]["semantic"]["predictions"]["y_pred"],
        )
    if "semantic" in split_data["modes"] and "full" in split_data["modes"]:
        yt = split_data["modes"]["semantic"]["predictions"]["y_true"]
        comparisons["semantic_vs_full_h2"] = mcnemar_test(
            yt,
            split_data["modes"]["semantic"]["predictions"]["y_pred"],
            split_data["modes"]["full"]["predictions"]["y_pred"],
        )
    if "judge" in split_data["modes"] and "full" in split_data["modes"]:
        yt = split_data["modes"]["judge"]["predictions"]["y_true"]
        comparisons["judge_vs_full"] = mcnemar_test(
            yt,
            split_data["modes"]["judge"]["predictions"]["y_pred"],
            split_data["modes"]["full"]["predictions"]["y_pred"],
        )
    analysis["comparisons"] = comparisons
    return analysis


def main():
    parser = argparse.ArgumentParser(description="Run statistical analysis on eval predictions")
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS_PATH)
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    args = parser.parse_args()

    if not args.predictions.exists():
        print(f"ERROR: Missing {args.predictions}. Run run_evaluation.py first.")
        sys.exit(1)

    with open(args.predictions, encoding="utf-8") as f:
        predictions = json.load(f)

    report = {"bootstrap_iterations": args.bootstrap_iterations, "splits": {}}
    for split in predictions.get("splits", {}):
        print(f"Analyzing split: {split}")
        report["splits"][split] = analyze_split(predictions, split)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "statistical_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    unseen = report["splits"].get("eval_unseen", {})
    if "full" in unseen.get("modes", {}):
        save_category_plot(
            unseen["modes"]["full"].get("category_breakdown", {}),
            "full",
            RESULTS_DIR / "category_breakdown.png",
        )

    print(f"\nSaved to {out_path}")
    for split, data in report["splits"].items():
        print(f"\n[{split}]")
        for comp_name, comp in data.get("comparisons", {}).items():
            sig = "SIGNIFICANT" if comp["significant_005"] else "not significant"
            print(f"  {comp_name}: p={comp['p_value']} ({sig})")


if __name__ == "__main__":
    main()
