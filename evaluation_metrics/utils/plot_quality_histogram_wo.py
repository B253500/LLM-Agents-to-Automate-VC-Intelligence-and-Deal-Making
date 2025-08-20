import glob
import json
import os
import sys
from typing import List

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


def collect_scores(dir_path: str) -> List[float]:
    out: List[float] = []
    for p in glob.glob(os.path.join(dir_path, "simple_metrics_*.json")):
        try:
            d = json.load(open(p))
            q = d.get("quality", {})
            v = q.get("score_without_readability")
            if isinstance(v, (int, float)):
                out.append(float(v))
        except Exception:
            continue
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "memo_evaluation_results"
    out_pdf = sys.argv[2] if len(sys.argv) > 2 else os.path.join("fig", "quality_score_histogram_wo.pdf")
    vals = collect_scores(src)
    if not vals:
        print("No scores found")
        sys.exit(1)
    q1 = percentile(vals, 0.25)
    med = percentile(vals, 0.5)
    q3 = percentile(vals, 0.75)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    s_min, s_max = min(vals), max(vals)
    padding = max(0.02, 0.05 * (s_max - s_min) if s_max > s_min else 0.05)
    x_left, x_right = s_min - padding, s_max + padding
    bins = max(6, int(len(vals) ** 0.5))
    ax.hist(vals, bins=bins, range=(x_left, x_right), color="#325b8c", edgecolor="white", alpha=0.85)
    ax.axvline(med, color="#b22222", linestyle="--", linewidth=1.2)
    band = ax.axvspan(q1, q3, color="#f5b7b1", alpha=0.30)
    ax.set_xlabel("Quality score (0–10) without readability (rescaled)")
    ax.set_ylabel(f"Count (n={len(vals)})")
    ax.set_title("Distribution of quality score (without readability)")
    from matplotlib.lines import Line2D
    median_handle = Line2D([0], [0], color="#b22222", linestyle="--", linewidth=1.2, label=f"Median {med:.2f}")
    band.set_label(f"IQR [{q1:.2f}, {q3:.2f}]")
    ax.legend(handles=[median_handle, band], frameon=True, loc="upper left", fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    fig.savefig(out_pdf, bbox_inches="tight")
    print(f"Saved {out_pdf}")


if __name__ == "__main__":
    main()


