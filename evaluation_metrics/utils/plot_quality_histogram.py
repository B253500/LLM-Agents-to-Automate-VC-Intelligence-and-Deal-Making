import glob
import json
import os
import sys
from typing import List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def percentile(values: List[float], p: float) -> float:
    vals = sorted(values)
    if not vals:
        return 0.0
    k = (len(vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    return vals[f] * (c - k) + vals[c] * (k - f)


def median_iqr(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    q1 = percentile(values, 0.25)
    med = percentile(values, 0.5)
    q3 = percentile(values, 0.75)
    return med, (q3 - q1)


def collect_quality_scores(metrics_dir: str) -> List[float]:
    scores: List[float] = []
    for path in glob.glob(os.path.join(metrics_dir, "simple_metrics_*.json")):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            q = data.get("quality", {}).get("score")
            if isinstance(q, (int, float)):
                scores.append(float(q))
        except Exception:
            continue
    return scores


def plot_hist(scores: List[float], out_pdf: str) -> None:
    q1, med, q3 = percentile(scores, 0.25), percentile(scores, 0.5), percentile(scores, 0.75)
    iqr = q3 - q1
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    # Dynamic x-range focused on observed span for visual clarity
    s_min, s_max = min(scores), max(scores)
    padding = max(0.02, 0.05 * (s_max - s_min) if s_max > s_min else 0.05)
    x_left, x_right = s_min - padding, s_max + padding
    bins = max(6, int(len(scores) ** 0.5))
    ax.hist(scores, bins=bins, range=(x_left, x_right), color="#325b8c", edgecolor="white", alpha=0.85)
    ax.axvline(med, color="#b22222", linestyle="--", linewidth=1.2)
    band = ax.axvspan(q1, q3, color="#f5b7b1", alpha=0.30)
    ax.set_xlabel("Quality score (0–10)")
    ax.set_ylabel(f"Count (n={len(scores)})")
    ax.set_title("Distribution of quality score")
    from matplotlib.lines import Line2D
    median_handle = Line2D([0], [0], color="#b22222", linestyle="--", linewidth=1.2, label=f"Median {med:.2f}")
    band.set_label(f"IQR [{q1:.2f}, {q3:.2f}]")
    ax.legend(handles=[median_handle, band], frameon=True, loc="upper left", fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def main():
    # Default metrics directory
    metrics_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("memo_evaluation_results")
    out_pdf = sys.argv[2] if len(sys.argv) > 2 else os.path.join("fig", "quality_score_histogram.pdf")
    scores = collect_quality_scores(metrics_dir)
    if not scores:
        print(f"No quality scores found in {metrics_dir}")
        sys.exit(1)
    plot_hist(scores, out_pdf)
    print(f"Saved {out_pdf}")


if __name__ == "__main__":
    main()


