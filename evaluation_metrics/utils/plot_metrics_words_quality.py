import csv
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


def col_from_csv(csv_path: str, name: str) -> List[float]:
    vals: List[float] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get(name)
            try:
                v = float(raw)
            except Exception:
                continue
            vals.append(v)
    return vals


def plot_hist(vals: List[float], xlabel: str, title: str, out_path: str) -> None:
    # Compute summary stats
    q1, med, q3 = percentile(vals, 0.25), percentile(vals, 0.5), percentile(vals, 0.75)
    iqr = q3 - q1

    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    bins = 10
    # Histogram bars
    ax.hist(vals, bins=bins, color="#325b8c", edgecolor="white", alpha=0.85)
    # Median line (red dashed)
    ax.axvline(med, color="#b22222", linestyle="--", linewidth=1.2)
    # IQR shading (soft pink)
    band = ax.axvspan(q1, q3, color="#f5b7b1", alpha=0.30)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"Count (n={len(vals)})")
    ax.set_title(title)

    # Legend entries that match the old style
    from matplotlib.lines import Line2D
    median_handle = Line2D([0], [0], color="#b22222", linestyle="--", linewidth=1.2, label=f"Median {med:.0f}")
    band.set_label(f"IQR [{q1:.0f}, {q3:.0f}]")
    ax.legend(handles=[median_handle, band], frameon=True, loc="upper left", fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_metrics_words_quality.py <aggregate_csv>")
        sys.exit(1)
    csv_path = sys.argv[1]
    words = col_from_csv(csv_path, "total_words")
    # Quality score lives in simple metrics JSON, not aggregate CSV by default; use score from 'quality' aggregate if present
    # As a fallback, we will try to read from per-run JSON if needed. Here, we plot words and leave quality to existing figure.
    plot_hist(words, "Total words", "Distribution of total words per memo", "fig/words_histogram_styled.pdf")
    print("Saved fig/words_histogram_styled.pdf")


if __name__ == "__main__":
    main()


