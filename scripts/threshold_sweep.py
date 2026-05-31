"""Threshold sensitivity and ROC/AUC analysis for Layer 1 semantic analyzer."""
import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import auc, roc_curve

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.env_setup  # noqa: F401, E402

from core.semantic_analyzer import SemanticAnalyzer

RESULTS_DIR = ROOT / "results"
DATASET_PATH = ROOT / "data" / "eval_dataset.json"


def load_dataset(limit: int | None = None) -> list[dict]:
    with open(DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data[:limit] if limit else data


def collect_scores(semantic: SemanticAnalyzer, dataset: list[dict]) -> tuple[list[int], list[float]]:
    y_true, scores = [], []
    for row in dataset:
        y_true.append(1 if row["label"] == "malicious" else 0)
        scores.append(semantic.max_similarity(row["text"]))
    return y_true, scores


def threshold_sweep(y_true: list[int], scores: list[float], thresholds: list[float]) -> list[dict]:
    results = []
    for threshold in thresholds:
        y_pred = [1 if s >= threshold else 0 for s in scores]
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
        tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        benign_total = fp + tn
        fp_rate = fp / benign_total if benign_total else 0.0
        results.append({
            "threshold": threshold,
            "f1": round(f1, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "fp_rate": round(fp_rate, 4),
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
        })
    return results


def save_roc_plot(y_true: list[int], scores: list[float], output: Path) -> float:
    fpr, tpr, _ = roc_curve(y_true, scores)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, label=f"ROC (AUC = {roc_auc:.4f})")
    plt.plot([0, 1], [0, 1], "k--", label="Random")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Layer 1 Semantic Analyzer — ROC Curve")
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return roc_auc


def main():
    parser = argparse.ArgumentParser(description="Semantic threshold sweep and ROC analysis")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threshold-min", type=float, default=0.70)
    parser.add_argument("--threshold-max", type=float, default=0.95)
    parser.add_argument("--threshold-step", type=float, default=0.05)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY required.")
        sys.exit(1)

    dataset = load_dataset(args.limit)
    semantic = SemanticAnalyzer()
    print(f"Collecting similarity scores for {len(dataset)} samples...")
    y_true, scores = collect_scores(semantic, dataset)

    thresholds = []
    t = args.threshold_min
    while t <= args.threshold_max + 1e-9:
        thresholds.append(round(t, 2))
        t += args.threshold_step

    sweep = threshold_sweep(y_true, scores, thresholds)
    current = float(os.getenv("SEMANTIC_THRESHOLD", "0.85"))
    current_row = min(sweep, key=lambda r: abs(r["threshold"] - current))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    roc_auc = save_roc_plot(y_true, scores, RESULTS_DIR / "roc_curve.png")

    report = {
        "samples": len(dataset),
        "roc_auc": round(roc_auc, 4),
        "selected_threshold": current,
        "selected_threshold_metrics": current_row,
        "best_f1_threshold": max(sweep, key=lambda r: r["f1"]),
        "sweep": sweep,
    }

    out_path = RESULTS_DIR / "threshold_sweep.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"ROC AUC: {roc_auc:.4f}")
    print(f"Selected threshold {current}: F1={current_row['f1']} FP_rate={current_row['fp_rate']}")
    print(f"Best F1 threshold: {report['best_f1_threshold']['threshold']} "
          f"(F1={report['best_f1_threshold']['f1']})")
    print(f"Saved to {out_path} and {RESULTS_DIR / 'roc_curve.png'}")


if __name__ == "__main__":
    main()
