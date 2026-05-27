"""Evaluate keyword, semantic, and full pipeline modes on eval_dataset.json."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.env_setup  # noqa: F401, E402

from core.judge_model import JudgeModel
from core.keyword_baseline import KeywordBaseline
from core.semantic_analyzer import SemanticAnalyzer

EVAL_PATH = ROOT / "data" / "eval_dataset.json"
RESULTS_DIR = ROOT / "results"


def load_dataset(limit: int | None = None) -> list[dict]:
    with open(EVAL_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if limit:
        data = data[:limit]
    return data


def compute_metrics(y_true: list[int], y_pred: list[int]) -> dict:
    tn = fp = fn = tp = 0
    for yt, yp in zip(y_true, y_pred):
        if yt == 1 and yp == 1:
            tp += 1
        elif yt == 1 and yp == 0:
            fn += 1
        elif yt == 0 and yp == 1:
            fp += 1
        else:
            tn += 1
    benign_total = fp + tn
    fp_rate = fp / benign_total if benign_total else 0.0
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "fp_rate": round(fp_rate, 4),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def run_keyword(dataset: list[dict]) -> dict:
    baseline = KeywordBaseline()
    y_true, y_pred, latencies = [], [], []
    for row in dataset:
        start = time.perf_counter()
        pred = baseline.is_attack(row["text"])
        latencies.append((time.perf_counter() - start) * 1000)
        y_true.append(1 if row["label"] == "malicious" else 0)
        y_pred.append(1 if pred else 0)
    metrics = compute_metrics(y_true, y_pred)
    metrics["latency_ms"] = {
        "mean": round(float(np.mean(latencies)), 2),
        "p50": round(float(np.percentile(latencies, 50)), 2),
        "p95": round(float(np.percentile(latencies, 95)), 2),
    }
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    return metrics


def run_semantic(dataset: list[dict], semantic: SemanticAnalyzer) -> dict:
    y_true, y_pred, latencies = [], [], []
    for row in dataset:
        start = time.perf_counter()
        pred, _ = semantic.analyze(row["text"])
        latencies.append((time.perf_counter() - start) * 1000)
        y_true.append(1 if row["label"] == "malicious" else 0)
        y_pred.append(1 if pred else 0)
    metrics = compute_metrics(y_true, y_pred)
    metrics["latency_ms"] = {
        "mean": round(float(np.mean(latencies)), 2),
        "p50": round(float(np.percentile(latencies, 50)), 2),
        "p95": round(float(np.percentile(latencies, 95)), 2),
    }
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    return metrics


def run_full(dataset: list[dict], semantic: SemanticAnalyzer, judge: JudgeModel) -> dict:
    y_true, y_pred, latencies = [], [], []
    for row in dataset:
        start = time.perf_counter()
        blocked, _ = semantic.analyze(row["text"])
        if not blocked:
            blocked = judge.analyze(row["text"])
        latencies.append((time.perf_counter() - start) * 1000)
        y_true.append(1 if row["label"] == "malicious" else 0)
        y_pred.append(1 if blocked else 0)
    metrics = compute_metrics(y_true, y_pred)
    metrics["latency_ms"] = {
        "mean": round(float(np.mean(latencies)), 2),
        "p50": round(float(np.percentile(latencies, 50)), 2),
        "p95": round(float(np.percentile(latencies, 95)), 2),
    }
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    return metrics


def save_confusion_plot(report: dict, output: Path):
    modes = ["keyword", "semantic", "full"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, mode in zip(axes, modes):
        cm = np.array(report["modes"][mode]["confusion_matrix"])
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(mode.capitalize())
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Benign", "Malicious"])
        ax.set_yticklabels(["Benign", "Malicious"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="black")
        fig.colorbar(im, ax=ax, fraction=0.046)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Run firewall evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit samples for pilot runs")
    parser.add_argument("--modes", nargs="+", default=["keyword", "semantic", "full"])
    args = parser.parse_args()

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    needs_openai = "semantic" in args.modes or "full" in args.modes
    if needs_openai and not api_key:
        print("ERROR: OPENAI_API_KEY required for semantic/full modes.")
        print(f"  Check {ROOT / '.env'} exists and contains OPENAI_API_KEY=sk-...")
        sys.exit(1)

    dataset = load_dataset(args.limit)
    report = {
        "samples": len(dataset),
        "targets": {"f1_min": 0.90, "fp_rate_max": 0.05, "latency_ms_max": 300},
        "modes": {},
    }

    if "keyword" in args.modes:
        print("Running keyword baseline...")
        report["modes"]["keyword"] = run_keyword(dataset)

    semantic = judge = None
    if "semantic" in args.modes or "full" in args.modes:
        semantic = SemanticAnalyzer()
        judge = JudgeModel()

    if "semantic" in args.modes:
        print("Running semantic-only mode...")
        report["modes"]["semantic"] = run_semantic(dataset, semantic)

    if "full" in args.modes:
        print("Running full pipeline mode...")
        report["modes"]["full"] = run_full(dataset, semantic, judge)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    plot_path = RESULTS_DIR / "confusion_matrix.png"
    if len(report["modes"]) >= 2:
        save_confusion_plot(report, plot_path)

    print(f"\nReport saved to {report_path}")
    for mode, m in report["modes"].items():
        print(
            f"  [{mode}] F1={m['f1']} FP_rate={m['fp_rate']} "
            f"latency_mean={m['latency_ms']['mean']}ms"
        )


if __name__ == "__main__":
    main()
