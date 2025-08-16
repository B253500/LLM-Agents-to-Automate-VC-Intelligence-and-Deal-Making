import os
import json
import glob
import sys
from typing import Dict, Any, List, Tuple


TARGET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "memo_evaluation_results"))


def percentile(values: List[float], p: float) -> float:
    vals = sorted([v for v in values if v is not None])
    if not vals:
        return 0.0
    k = (len(vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    d0 = vals[f] * (c - k)
    d1 = vals[c] * (k - f)
    return d0 + d1


def median_iqr(values: List[float]) -> Tuple[float, float]:
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return 0.0, 0.0
    med = percentile(vals, 0.5)
    q1 = percentile(vals, 0.25)
    q3 = percentile(vals, 0.75)
    return med, (q3 - q1)


AGENTS = [
    "COMPLETE ANALYSIS PIPELINE",
    "DECK AGENT",
    "TECHNICAL DD AGENT",
    "TEAM AGENT",
    "MARKET SIZING AGENT",
    "FINANCIAL ANALYSIS AGENT",
    "COMPETITORS AGENT",
    "RISK ASSESSMENT AGENT",
    "BUSINESS MODEL AGENT",
    "PRODUCT AGENT",
    "ESG AGENT",
    "EXIT AGENT",
    "FOLLOW-UP AGENT",
]

DERIVED_BUCKETS = [
    "total_agent_runtime",
    "analysis_agent_runtime",
    "synthesis_agent_runtime",
    "extraction_runtime",
    "visuals_runtime",
    "document_creation_runtime",
    "other_processes_runtime",
]


def load_simple_runs(base_dir: str) -> List[Dict[str, Any]]:
    paths = sorted(glob.glob(os.path.join(base_dir, "simple_metrics_*.json")))
    runs = []
    for p in paths:
        try:
            with open(p, "r") as f:
                data = json.load(f)
                data["__file"] = os.path.basename(p)
                runs.append(data)
        except Exception:
            continue
    return runs


def main():
    base_dir = TARGET_DIR
    if len(sys.argv) >= 2:
        base_dir = os.path.abspath(sys.argv[1])

    runs = load_simple_runs(base_dir)
    if not runs:
        print(f"No simple_metrics_*.json found in {base_dir}")
        return

    # Collect per-run rows for CSV
    rows: List[Dict[str, Any]] = []

    # Aggregation containers
    per_key_times: Dict[str, List[float]] = {k: [] for k in AGENTS + DERIVED_BUCKETS}
    total_words_list: List[int] = []
    dup_ratio_list: List[float] = []
    dup_count_list: List[int] = []
    unk_outside_list: List[int] = []
    unk_including_list: List[int] = []
    mermaid_present_list: List[bool] = []

    # Section pass counts
    section_pass_counts: Dict[str, int] = {}
    section_total_counts: Dict[str, int] = {}

    for r in runs:
        timing = r.get("timing", {}) or {}
        run_info = r.get("run_info", {}) or {}
        dup = r.get("duplicates_unknowns", {}) or {}
        visuals = r.get("visuals", {}) or {}
        section_checks = r.get("section_checks", {}) or {}

        # CSV row
        row = {"file": r.get("__file", "")}

        # Per-agent and derived timings
        for key in AGENTS + DERIVED_BUCKETS:
            val = timing.get(key)
            if isinstance(val, (int, float)):
                per_key_times[key].append(float(val))
                row[key] = float(val)
            else:
                row[key] = None

        # Words
        words = run_info.get("total_words")
        if isinstance(words, int):
            total_words_list.append(words)
            row["total_words"] = words
        else:
            row["total_words"] = None

        # Duplicates/unknowns
        dup_ratio = dup.get("duplicate_ratio")
        dup_count = dup.get("duplicate_count")
        unk_out = dup.get("unknown_count_outside_risks")
        unk_inc = dup.get("unknown_count_including_risks")
        if isinstance(dup_ratio, (int, float)):
            dup_ratio_list.append(float(dup_ratio))
        if isinstance(dup_count, int):
            dup_count_list.append(dup_count)
        if isinstance(unk_out, int):
            unk_outside_list.append(unk_out)
        if isinstance(unk_inc, int):
            unk_including_list.append(unk_inc)
        row.update({
            "duplicate_ratio": dup_ratio,
            "duplicate_count": dup_count,
            "unknown_outside_risks": unk_out,
            "unknown_including_risks": unk_inc,
        })

        # Visuals
        mermaid = bool(visuals.get("mermaid_present", False))
        mermaid_present_list.append(mermaid)
        row["mermaid_present"] = mermaid

        # Section checks pass/fail
        for sec, result in section_checks.items():
            passed = bool(result.get("pass")) if isinstance(result, dict) else bool(result)
            section_pass_counts[sec] = section_pass_counts.get(sec, 0) + (1 if passed else 0)
            section_total_counts[sec] = section_total_counts.get(sec, 0) + 1
            # include per-row columns for convenience
            row[f"sec_{sec}_pass"] = passed

        rows.append(row)

    # Compute medians and IQRs
    summary_lines: List[str] = []
    summary_lines.append("# Aggregate Summary (simple metrics)")
    summary_lines.append("")
    summary_lines.append(f"Runs aggregated: {len(runs)}")

    # Overall timing
    med, iqr = median_iqr(per_key_times["COMPLETE ANALYSIS PIPELINE"])
    summary_lines.append(f"- Timing (overall) — median: {med:.1f}s, IQR: {iqr:.1f}s")

    # Per-agent timing
    summary_lines.append("- Timing by agent (median, IQR in seconds):")
    for key in AGENTS:
        med, iqr = median_iqr(per_key_times[key])
        summary_lines.append(f"  - {key}: {med:.1f}s (IQR {iqr:.1f}s)")

    # Derived buckets
    summary_lines.append("- Derived runtimes (median, IQR in seconds):")
    for key in DERIVED_BUCKETS:
        med, iqr = median_iqr(per_key_times[key])
        summary_lines.append(f"  - {key}: {med:.1f}s (IQR {iqr:.1f}s)")

    # Words
    med_words, iqr_words = median_iqr([float(w) for w in total_words_list])
    summary_lines.append(f"- Words (total) — median: {med_words:.0f}, IQR: {iqr_words:.0f}")

    # Duplicates & unknowns
    med_dup_ratio, iqr_dup_ratio = median_iqr(dup_ratio_list)
    med_dup_count, iqr_dup_count = median_iqr([float(x) for x in dup_count_list])
    med_unk_out, iqr_unk_out = median_iqr([float(x) for x in unk_outside_list])
    med_unk_inc, iqr_unk_inc = median_iqr([float(x) for x in unk_including_list])
    summary_lines.append(f"- Duplicate ratio — median: {med_dup_ratio:.3f}, IQR: {iqr_dup_ratio:.3f}")
    summary_lines.append(f"- Duplicate count — median: {med_dup_count:.0f}, IQR: {iqr_dup_count:.0f}")
    summary_lines.append(f"- Unknowns (outside risks) — median: {med_unk_out:.0f}, IQR: {iqr_unk_out:.0f}")
    summary_lines.append(f"- Unknowns (including risks) — median: {med_unk_inc:.0f}, IQR: {iqr_unk_inc:.0f}")

    # Visuals rate
    visuals_rate = (sum(1 for v in mermaid_present_list if v) / len(mermaid_present_list)) * 100.0
    summary_lines.append(f"- Visuals (Mermaid) presence: {visuals_rate:.1f}% of runs")

    # Other processes explanation
    summary_lines.append("- other_processes_runtime includes: orchestration overhead, context building, enrichment outside agent wrappers, and memo/post-processing.")

    # Section pass rates
    summary_lines.append("- Section checks pass rates:")
    for sec in sorted(section_total_counts.keys()):
        total = section_total_counts.get(sec, 0) or 1
        passed = section_pass_counts.get(sec, 0)
        rate = (passed / total) * 100.0
        summary_lines.append(f"  - {sec}: {rate:.1f}%")

    # Write markdown summary
    md_path = os.path.join(base_dir, "aggregate_simple_summary.md")
    with open(md_path, "w") as f:
        f.write("\n".join(summary_lines) + "\n")
    print(f"Saved: {md_path}")

    # Write per-run CSV
    import csv
    csv_path = os.path.join(base_dir, "aggregate_simple_runs.csv")
    fieldnames = [
        "file",
        *AGENTS,
        *DERIVED_BUCKETS,
        "total_words",
        "duplicate_ratio",
        "duplicate_count",
        "unknown_outside_risks",
        "unknown_including_risks",
        "mermaid_present",
    ]
    # Also include per-section pass columns present in rows
    dynamic_sec_cols = sorted({k for r in rows for k in r.keys() if k.startswith("sec_")})
    fieldnames.extend(dynamic_sec_cols)
    with open(csv_path, "w", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})
    print(f"Saved: {csv_path}")

    # Write per-section pass rates CSV
    sec_csv = os.path.join(base_dir, "aggregate_section_pass_rates.csv")
    with open(sec_csv, "w", newline="") as sf:
        writer = csv.writer(sf)
        writer.writerow(["section", "pass_rate_percent", "passed", "total_runs"])
        for sec in sorted(section_total_counts.keys()):
            total = section_total_counts.get(sec, 0)
            passed = section_pass_counts.get(sec, 0)
            rate = (passed / total * 100.0) if total else 0.0
            writer.writerow([sec, f"{rate:.1f}", passed, total])
    print(f"Saved: {sec_csv}")


if __name__ == "__main__":
    main()


