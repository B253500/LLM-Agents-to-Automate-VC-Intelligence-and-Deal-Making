import csv
import os
import sys
from typing import List, Tuple

import matplotlib

# Use a non-interactive backend for headless environments
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


def median(values: List[float]) -> float:
    return percentile(values, 0.5)


def read_columns(csv_path: str, cols: List[str]) -> List[List[float]]:
    data: List[List[float]] = [[] for _ in cols]
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for i, col in enumerate(cols):
                raw = row.get(col)
                try:
                    val = float(raw) if raw not in (None, "", "None", "nan") else None
                except Exception:
                    val = None
                if isinstance(val, float):
                    data[i].append(val)
    return data


def make_runtime_pie(seconds_analysis: float, seconds_synthesis: float, seconds_other: float, out_pdf: str, out_png: str) -> None:
    # Convert seconds to minutes for labeling
    mins_analysis = seconds_analysis / 60.0
    mins_synthesis = seconds_synthesis / 60.0
    mins_other = seconds_other / 60.0

    labels = [
        f"Analysis agents ({mins_analysis:.2f} min)",
        f"Synthesis agents ({mins_synthesis:.2f} min)",
        f"Other processes ({mins_other:.2f} min)",
    ]
    sizes = [seconds_analysis, seconds_synthesis, seconds_other]
    colors = ["#4C78A8", "#F58518", "#72B7B2"]

    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        pctdistance=0.8,
        textprops={"fontsize": 10},
    )
    ax.axis("equal")
    ax.set_title("Median runtime breakdown", fontsize=12)

    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def main():
    if len(sys.argv) < 4:
        print("Usage: python plot_runtime_pie.py <aggregate_csv> <out_pdf> <out_png>")
        sys.exit(1)

    csv_path = sys.argv[1]
    out_pdf = sys.argv[2]
    out_png = sys.argv[3]

    # Columns expected in aggregate_simple_runs.csv (seconds)
    columns = [
        "analysis_agent_runtime",
        "synthesis_agent_runtime",
        "other_processes_runtime",
    ]
    series = read_columns(csv_path, columns)
    medians_sec: List[float] = [median(col_vals) for col_vals in series]

    analysis_s, synthesis_s, other_s = medians_sec
    make_runtime_pie(analysis_s, synthesis_s, other_s, out_pdf, out_png)
    print(f"Saved pie chart to {out_pdf} and {out_png}")


if __name__ == "__main__":
    main()


