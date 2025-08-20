import glob
import json
import os
import sys
import csv
from typing import Dict, Any


def soft_pass(section: str, data: Dict[str, Any]) -> bool:
    name = section.strip().upper()
    # COMPANY OVERVIEW: pass if >=3 of {sector, website, team, funding_stage}
    if name == "COMPANY OVERVIEW":
        keys = ["sector", "website", "team", "funding_stage"]
        present = sum(1 for k in keys if bool(data.get(k)))
        return present >= 3

    # FINANCIAL ANALYSIS: pass if has_numeric OR link_count >= 1
    if name == "FINANCIAL ANALYSIS":
        has_numeric = bool(data.get("has_numeric"))
        link_count = data.get("link_count")
        try:
            link_count_val = int(link_count) if link_count is not None else None
        except Exception:
            link_count_val = None
        if link_count_val is None:
            link_ok = False
        else:
            link_ok = link_count_val >= 1
        return bool(has_numeric or link_ok)

    # TEAM & MANAGEMENT: pass if executives >= 2 OR has_linkedin true
    if name == "TEAM & MANAGEMENT":
        execs = data.get("executives")
        try:
            execs_val = int(execs) if execs is not None else 0
        except Exception:
            execs_val = 0
        has_linkedin = bool(data.get("has_linkedin"))
        return execs_val >= 2 or has_linkedin

    # MARKET SIZE & ANALYSIS: pass if has_numeric AND link_count >= 1
    if name == "MARKET SIZE & ANALYSIS":
        has_numeric = bool(data.get("has_numeric"))
        link_count = data.get("link_count")
        try:
            link_val = int(link_count) if link_count is not None else 0
        except Exception:
            link_val = 0
        return bool(has_numeric and link_val >= 1)

    # COMPETITORS: pass if count >= 2
    if name == "COMPETITORS":
        cnt = data.get("count")
        try:
            cnt_val = int(cnt) if cnt is not None else 0
        except Exception:
            cnt_val = 0
        return cnt_val >= 2

    # Default: keep original pass if present; else best-effort truthiness
    return bool(data.get("pass", False))


def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("memo_evaluation_results")
    mode = sys.argv[2] if len(sys.argv) > 2 else "loose"  # loose | mid
    paths = sorted(glob.glob(os.path.join(base_dir, "simple_metrics_*.json")))
    if not paths:
        print(f"No simple_metrics_*.json in {base_dir}")
        sys.exit(0)

    pass_counts: Dict[str, int] = {}
    totals: Dict[str, int] = {}

    for p in paths:
        try:
            with open(p, "r") as f:
                d = json.load(f)
        except Exception:
            continue
        checks = d.get("section_checks", {}) or {}
        for sec, meta in checks.items():
            meta_d = meta if isinstance(meta, dict) else {"pass": bool(meta)}
            # Apply mode-specific overrides
            name = sec.strip().upper()
            if mode == "mid":
                # Company overview: require sector present AND at least 3/4 items overall
                if name == "COMPANY OVERVIEW":
                    keys = ["sector", "website", "team", "funding_stage"]
                    present = sum(1 for k in keys if bool(meta_d.get(k)))
                    result = bool(meta_d.get("sector")) and present >= 3
                # Financial analysis: require numeric AND at least 1 link
                elif name == "FINANCIAL ANALYSIS":
                    has_numeric = bool(meta_d.get("has_numeric"))
                    try:
                        link_ok = int(meta_d.get("link_count") or 0) >= 1
                    except Exception:
                        link_ok = False
                    result = bool(has_numeric and link_ok)
                # Team & management: require executives >= 2 AND (has_linkedin OR executives >= 3)
                elif name == "TEAM & MANAGEMENT":
                    try:
                        execs = int(meta_d.get("executives") or 0)
                    except Exception:
                        execs = 0
                    has_li = bool(meta_d.get("has_linkedin"))
                    result = (execs >= 2) and (has_li or execs >= 3)
                # Market size & analysis: require numeric AND ≥1 link (same as loose)
                elif name == "MARKET SIZE & ANALYSIS":
                    has_numeric = bool(meta_d.get("has_numeric"))
                    try:
                        link_ok = int(meta_d.get("link_count") or 0) >= 1
                    except Exception:
                        link_ok = False
                    result = bool(has_numeric and link_ok)
                # Competitors: keep loose rule >=2
                else:
                    result = soft_pass(sec, meta_d)
            else:
                result = soft_pass(sec, meta_d)
            totals[sec] = totals.get(sec, 0) + 1
            if result:
                pass_counts[sec] = pass_counts.get(sec, 0) + 1

    # Write updated pass rates CSV
    out_csv = os.path.join(base_dir, "aggregate_section_pass_rates.csv")
    with open(out_csv, "w", newline="") as sf:
        writer = csv.writer(sf)
        writer.writerow(["section", "pass_rate_percent", "passed", "total_runs"])
        for sec in sorted(totals.keys()):
            total = totals[sec]
            passed = pass_counts.get(sec, 0)
            rate = (passed / total * 100.0) if total else 0.0
            writer.writerow([sec, f"{rate:.1f}", passed, total])
    print(f"Saved {out_csv} ({mode})")


if __name__ == "__main__":
    main()


