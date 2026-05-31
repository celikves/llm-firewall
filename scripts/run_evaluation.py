"""Evaluate keyword, semantic, judge, and full pipeline modes on eval datasets."""
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

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

DATASET_FILES = {
    "eval_seen": DATA_DIR / "eval_seen.json",
    "eval_unseen": DATA_DIR / "eval_unseen.json",
    "eval_benign": DATA_DIR / "eval_benign.json",
    "combined": DATA_DIR / "eval_dataset.json",
}

ALL_MODES = ["keyword", "semantic", "judge", "full"]


def load_dataset(name: str, limit: int | None = None) -> list[dict]:
    path = DATASET_FILES.get(name, DATA_DIR / f"{name}.json")
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset {path}. Run build_eval_dataset.py first.")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if limit:
        data = data[:limit]
    return data


def load_eval_split(name: str, limit: int | None = None) -> list[dict]:
    """Load malicious split and attach benign samples for combined evaluation."""
    malicious = load_dataset(name, limit=None)
    benign = load_dataset("eval_benign", limit=None)
    if name == "eval_seen":
        mal_limit = limit
        ben_limit = limit
    elif name == "eval_unseen":
        mal_limit = limit
        ben_limit = limit
    elif limit:
        mal_limit = max(1, limit // 2)
        ben_limit = limit - mal_limit
    else:
        mal_limit = ben_limit = None

    if mal_limit:
        malicious = malicious[:mal_limit]
    if ben_limit:
        benign = benign[:ben_limit]
    combined = malicious + benign
    return combined


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


def _latency_stats(latencies: list[float]) -> dict:
    return {
        "mean": round(float(np.mean(latencies)), 2),
        "p50": round(float(np.percentile(latencies, 50)), 2),
        "p95": round(float(np.percentile(latencies, 95)), 2),
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
    metrics["latency_ms"] = _latency_stats(latencies)
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    metrics["predictions"] = {"y_true": y_true, "y_pred": y_pred}
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
    metrics["latency_ms"] = _latency_stats(latencies)
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    metrics["predictions"] = {"y_true": y_true, "y_pred": y_pred}
    return metrics


def run_judge(dataset: list[dict], judge: JudgeModel) -> dict:
    y_true, y_pred, latencies = [], [], []
    for row in dataset:
        start = time.perf_counter()
        pred = judge.analyze(row["text"])
        latencies.append((time.perf_counter() - start) * 1000)
        y_true.append(1 if row["label"] == "malicious" else 0)
        y_pred.append(1 if pred else 0)
    metrics = compute_metrics(y_true, y_pred)
    metrics["latency_ms"] = _latency_stats(latencies)
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    metrics["predictions"] = {"y_true": y_true, "y_pred": y_pred}
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
    metrics["latency_ms"] = _latency_stats(latencies)
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    metrics["predictions"] = {"y_true": y_true, "y_pred": y_pred}
    return metrics


def run_modes(
    dataset: list[dict],
    modes: list[str],
    semantic: SemanticAnalyzer | None = None,
    judge: JudgeModel | None = None,
) -> dict:
    results = {}
    if "keyword" in modes:
        print("  Running keyword baseline...")
        results["keyword"] = run_keyword(dataset)
    if "semantic" in modes:
        print("  Running semantic-only mode...")
        results["semantic"] = run_semantic(dataset, semantic)
    if "judge" in modes:
        print("  Running judge-only mode...")
        results["judge"] = run_judge(dataset, judge)
    if "full" in modes:
        print("  Running full pipeline mode...")
        results["full"] = run_full(dataset, semantic, judge)
    return results


def strip_predictions(report: dict) -> dict:
    """Remove raw predictions from saved report (kept in memory for stats script)."""
    cleaned = json.loads(json.dumps(report))
    for split_data in cleaned.get("splits", {}).values():
        for mode_data in split_data.get("modes", {}).values():
            mode_data.pop("predictions", None)
    if "modes" in cleaned:
        for mode_data in cleaned["modes"].values():
            mode_data.pop("predictions", None)
    return cleaned


def save_confusion_plot(report: dict, output: Path, split_key: str = "combined"):
    splits = report.get("splits", {})
    if split_key in splits:
        modes_data = splits[split_key]["modes"]
    else:
        modes_data = report.get("modes", {})

    modes = [m for m in ALL_MODES if m in modes_data]
    if not modes:
        return

    fig, axes = plt.subplots(1, len(modes), figsize=(4 * len(modes), 4))
    if len(modes) == 1:
        axes = [axes]
    for ax, mode in zip(axes, modes):
        cm = np.array(modes_data[mode]["confusion_matrix"])
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
    plt.suptitle(f"Confusion matrices — {split_key}")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Run firewall evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit samples per split (pilot runs)")
    parser.add_argument("--modes", nargs="+", default=ALL_MODES)
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["eval_seen", "eval_unseen", "combined"],
        help="Dataset splits to evaluate",
    )
    args = parser.parse_args()

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    needs_openai = any(m in args.modes for m in ("semantic", "judge", "full"))
    if needs_openai and not api_key:
        print("ERROR: OPENAI_API_KEY required for semantic/judge/full modes.")
        print(f"  Check {ROOT / '.env'} exists and contains OPENAI_API_KEY=sk-...")
        sys.exit(1)

    semantic = judge = None
    if any(m in args.modes for m in ("semantic", "full")):
        semantic = SemanticAnalyzer()
    if any(m in args.modes for m in ("judge", "full")):
        judge = JudgeModel()

    report = {
        "targets": {"f1_min": 0.90, "fp_rate_max": 0.05, "latency_ms_max": 300},
        "modes": args.modes,
        "splits": {},
    }

    for split in args.splits:
        print(f"\n=== Split: {split} ===")
        if split == "combined":
            dataset = load_dataset("combined", args.limit)
        else:
            dataset = load_eval_split(split, args.limit)
        print(f"Samples: {len(dataset)}")
        split_results = run_modes(dataset, args.modes, semantic, judge)
        report["splits"][split] = {"samples": len(dataset), "modes": split_results}

    # Backward-compatible top-level combined modes
    if "combined" in report["splits"]:
        report["samples"] = report["splits"]["combined"]["samples"]
        report["modes"] = report["splits"]["combined"]["modes"]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "eval_report.json"
    predictions_path = RESULTS_DIR / "eval_predictions.json"

    with open(predictions_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(strip_predictions(report), f, indent=2)

    plot_path = RESULTS_DIR / "confusion_matrix.png"
    save_confusion_plot(report, plot_path, "combined")

    print(f"\nReport saved to {report_path}")
    print(f"Predictions saved to {predictions_path}")
    for split, split_data in report["splits"].items():
        print(f"\n[{split}]")
        for mode, m in split_data["modes"].items():
            print(
                f"  {mode}: F1={m['f1']} FP_rate={m['fp_rate']} "
                f"latency_mean={m['latency_ms']['mean']}ms"
            )


if __name__ == "__main__":
    main()
