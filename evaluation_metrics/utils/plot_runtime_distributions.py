import csv
import os
import sys
from typing import List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def percentile(values: List[float], p: float) -> float:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return 0.0
    if p <= 0:
        return vals[0]
    if p >= 1:
        return vals[-1]
    k = (len(vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    d0 = vals[f] * (c - k)
    d1 = vals[c] * (k - f)
    return d0 + d1


def median_iqr(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    q1 = percentile(values, 0.25)
    med = percentile(values, 0.5)
    q3 = percentile(values, 0.75)
    return med, (q3 - q1)


def read_column(csv_path: str, col: str) -> List[float]:
    vals: List[float] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get(col)
            try:
                v = float(raw)
            except Exception:
                continue
            vals.append(v)
    return vals


def plot_side_by_side(minutes_a: List[float], minutes_b: List[float], out_pdf: str, out_png: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=150, sharey=True)

    # Left: Complete memo runtime
    ax = axes[0]
    ax.hist(minutes_a, bins=10, color="#4C78A8", alpha=0.85, edgecolor="white")
    med_a, iqr_a = median_iqr([x * 60 for x in minutes_a])  # compute on seconds for consistency, convert later
    med_a_min = med_a / 60.0
    ax.axvline(med_a_min, color="#333333", linestyle="--", linewidth=1)
    ax.set_title("Complete memo runtime")
    ax.set_xlabel("Minutes")
    ax.set_ylabel("Count")
    ax.text(0.98, 0.95, f"Median {med_a_min:.2f}\nIQR {iqr_a/60.0:.2f}", transform=ax.transAxes,
            ha="right", va="top", fontsize=9, bbox=dict(facecolor="white", alpha=0.8, edgecolor="#dddddd"))

    # Right: Total agent runtime
    ax = axes[1]
    ax.hist(minutes_b, bins=10, color="#F58518", alpha=0.85, edgecolor="white")
    med_b, iqr_b = median_iqr([x * 60 for x in minutes_b])
    med_b_min = med_b / 60.0
    ax.axvline(med_b_min, color="#333333", linestyle="--", linewidth=1)
    ax.set_title("Total agent runtime")
    ax.set_xlabel("Minutes")
    ax.text(0.98, 0.95, f"Median {med_b_min:.2f}\nIQR {iqr_b/60.0:.2f}", transform=ax.transAxes,
            ha="right", va="top", fontsize=9, bbox=dict(facecolor="white", alpha=0.8, edgecolor="#dddddd"))

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def main():
    if len(sys.argv) < 4:
        print("Usage: python plot_runtime_distributions.py <aggregate_csv> <out_pdf> <out_png>")
        sys.exit(1)
    csv_path, out_pdf, out_png = sys.argv[1:4]

    comp_s = read_column(csv_path, "COMPLETE ANALYSIS PIPELINE")
    agent_s = read_column(csv_path, "total_agent_runtime")
    comp_m = [s / 60.0 for s in comp_s]
    agent_m = [s / 60.0 for s in agent_s]

    plot_side_by_side(comp_m, agent_m, out_pdf, out_png)
    print(f"Saved {out_pdf} and {out_png}")


if __name__ == "__main__":
    main()


