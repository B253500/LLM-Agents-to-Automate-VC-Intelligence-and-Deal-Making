import csv
import json
import os
import sys
from typing import List, Dict, Tuple


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
    med = percentile(values, 0.5)
    q1 = percentile(values, 0.25)
    q3 = percentile(values, 0.75)
    return med, (q3 - q1)


def safe_float(x: str) -> float:
    try:
        if x in (None, "", "None", "nan"):
            return None
        return float(x)
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python derive_runtime_summary.py <aggregate_simple_runs.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        sys.exit(1)

    total: List[float] = []
    total_agent: List[float] = []
    analysis: List[float] = []
    synthesis: List[float] = []
    residual_other: List[float] = []

    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = safe_float(row.get("COMPLETE ANALYSIS PIPELINE"))
            a = safe_float(row.get("total_agent_runtime"))
            an = safe_float(row.get("analysis_agent_runtime"))
            sy = safe_float(row.get("synthesis_agent_runtime"))
            if t is not None:
                total.append(t)
            if a is not None:
                total_agent.append(a)
            if an is not None:
                analysis.append(an)
            if sy is not None:
                synthesis.append(sy)
            if t is not None and a is not None:
                residual_other.append(max(t - a, 0.0))

    total_med, total_iqr = median_iqr(total)
    agent_med, agent_iqr = median_iqr(total_agent)
    analysis_med, analysis_iqr = median_iqr(analysis)
    synthesis_med, synthesis_iqr = median_iqr(synthesis)
    other_med, other_iqr = median_iqr(residual_other)

    out: Dict[str, Dict[str, float]] = {
        "complete_analysis_pipeline_s": {"median": total_med, "iqr": total_iqr},
        "total_agent_runtime_s": {"median": agent_med, "iqr": agent_iqr},
        "analysis_agent_runtime_s": {"median": analysis_med, "iqr": analysis_iqr},
        "synthesis_agent_runtime_s": {"median": synthesis_med, "iqr": synthesis_iqr},
        "other_processes_runtime_s": {"median": other_med, "iqr": other_iqr},
        "consistency_check": {
            "median_total_minutes": total_med / 60.0,
            "median_analysis_minutes": analysis_med / 60.0,
            "median_synthesis_minutes": synthesis_med / 60.0,
            "median_other_minutes": other_med / 60.0,
            "sum_of_components_minutes": (analysis_med + synthesis_med + other_med) / 60.0,
        },
    }

    out_json = os.path.join(os.path.dirname(csv_path), "runtime_summary_derived.json")
    with open(out_json, "w") as jf:
        json.dump(out, jf, indent=2)
    print(f"Saved {out_json}")

    # Also print a LaTeX-ready line set in minutes (rounded to 2 dp)
    cm = out["complete_analysis_pipeline_s"]["median"] / 60.0
    ci = out["complete_analysis_pipeline_s"]["iqr"] / 60.0
    tam = out["total_agent_runtime_s"]["median"] / 60.0
    tai = out["total_agent_runtime_s"]["iqr"] / 60.0
    anm = out["analysis_agent_runtime_s"]["median"] / 60.0
    ani = out["analysis_agent_runtime_s"]["iqr"] / 60.0
    sym = out["synthesis_agent_runtime_s"]["median"] / 60.0
    syi = out["synthesis_agent_runtime_s"]["iqr"] / 60.0
    otm = out["other_processes_runtime_s"]["median"] / 60.0
    oti = out["other_processes_runtime_s"]["iqr"] / 60.0

    print("LaTeX (minutes, medians with IQR):")
    print(f"Complete memo runtime & {cm:.2f} & {ci:.2f} \\")
    print(f"Total agent runtime & {tam:.2f} & {tai:.2f} \\")
    print(f"Analysis agent runtime & {anm:.2f} & {ani:.2f} \\")
    print(f"Synthesis agent runtime & {sym:.2f} & {syi:.2f} \\")
    print(f"Other processes (derived) & {otm:.2f} & {oti:.2f} \\")


if __name__ == "__main__":
    main()


