import csv
import math
import os
import sys
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402


AGENTS = [
    # First row emphasis
    "DECK AGENT",
    "PRODUCT AGENT",
    "TEAM AGENT",
    "ESG AGENT",
    # Remaining (order by relatedness)
    "MARKET SIZING AGENT",
    "FINANCIAL ANALYSIS AGENT",
    "COMPETITORS AGENT",
    "RISK ASSESSMENT AGENT",
    "BUSINESS MODEL AGENT",
    "TECHNICAL DD AGENT",
    "EXIT AGENT",
    "FOLLOW-UP AGENT",
]


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


def quartiles(values: List[float]) -> Tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    q1 = percentile(values, 0.25)
    med = percentile(values, 0.5)
    q3 = percentile(values, 0.75)
    return q1, med, q3


def read_columns(csv_path: str, cols: List[str]) -> Dict[str, List[float]]:
    data: Dict[str, List[float]] = {c: [] for c in cols}
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for c in cols:
                raw = row.get(c)
                try:
                    s = float(raw)
                except Exception:
                    continue
                data[c].append(s / 60.0)  # store as minutes
    return data


def plot_histograms(agent_to_minutes: Dict[str, List[float]], out_pdf: str, out_png: str) -> None:
    n = len(agent_to_minutes)
    rows, cols = 3, 4
    fig, axes = plt.subplots(rows, cols, figsize=(12, 8), dpi=150, sharey=False)
    axes = axes.flatten()

    for idx, agent in enumerate(AGENTS):
        ax = axes[idx]
        mins = agent_to_minutes.get(agent, [])
        # Adaptive bins via Freedman–Diaconis rule (on minutes) to avoid overly wide bars
        if mins and len(mins) >= 2:
            # compute IQR in minutes from secs IQR already computed
            iqr_m = (iqr_s / 60.0) if 'iqr_s' in locals() else (percentile(mins, 0.75) - percentile(mins, 0.25))
            data_range = max(mins) - min(mins)
            if iqr_m > 0 and data_range > 0:
                bin_width = 2 * iqr_m * (len(mins) ** (-1/3))
                num_bins = max(8, min(25, int(math.ceil(data_range / bin_width))))
            else:
                num_bins = 12
        else:
            num_bins = 6
        # Plot counts (not density)
        ax.hist(mins, bins=num_bins, color="#4C78A8", alpha=0.85, edgecolor="white", density=False)
        # compute median/IQR in seconds then convert
        secs = [m * 60.0 for m in mins]
        q1_s, med_s, q3_s = quartiles(secs)
        iqr_s = q3_s - q1_s
        med_m = med_s / 60.0
        q1_m = q1_s / 60.0
        q3_m = q3_s / 60.0
        ax.axvline(med_m, color="#333333", linestyle="--", linewidth=1)
        # Shade IQR band
        ax.axvspan(q1_m, q3_m, color="#4C78A8", alpha=0.12)
        ax.set_title(agent, fontsize=10)
        # Per-agent x-limit based on 95th percentile to avoid outliers compressing the plot
        if mins:
            p95 = percentile(mins, 0.95)
            xmax = max(mins)
            # also compute median + 1.5*IQR (converted to minutes)
            right_iqr = med_m + 1.5 * (iqr_s / 60.0)
            # choose the tighter cap to better resemble 10-run visuals
            cap = min(p95, right_iqr)
            right = max(cap, med_m) * 1.10
            right = min(right, xmax * 1.10) if math.isfinite(xmax) else right
            right = max(right, 0.2)  # ensure some width
            ax.set_xlim(0, right)
        else:
            ax.set_xlim(0, 1.0)
        # Y-axis as integer counts with fewer tick labels
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
        if idx % cols == 0:
            ax.set_ylabel("Count")
        ax.set_xlabel("Minutes")
        ax.text(
            0.98,
            0.95,
            f"Median {med_m:.2f} (IQR {iqr_s/60.0:.2f})\n n={len(mins)}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8,
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="#dddddd"),
        )

        # Custom y-limits: first row 0–50, others 0–30
        if agent in {"DECK AGENT", "PRODUCT AGENT", "TEAM AGENT", "ESG AGENT"}:
            ax.set_ylim(0, 50)
        else:
            ax.set_ylim(0, 30)

    # Hide any unused axes (shouldn't happen with 12 agents and 3x4 grid)
    for j in range(idx + 1, rows * cols):
        axes[j].axis("off")

    fig.suptitle("Per-agent runtime histograms (minutes)", fontsize=12)
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, bbox_inches="tight")


def main():
    if len(sys.argv) < 4:
        print("Usage: python plot_agent_runtime_histograms.py <aggregate_csv> <out_pdf> <out_png>")
        sys.exit(1)
    csv_path, out_pdf, out_png = sys.argv[1:4]
    data = read_columns(csv_path, AGENTS)
    plot_histograms(data, out_pdf, out_png)
    print(f"Saved {out_pdf} and {out_png}")


if __name__ == "__main__":
    main()


