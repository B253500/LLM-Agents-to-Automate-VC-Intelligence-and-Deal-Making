import json
import os
import glob
from statistics import mean
import csv

EVAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "evaluation_results"))

# Prices per 1K tokens (align with evaluation_metrics.py defaults)
PRICE_PER_1K = {
    "gpt-4": 0.03,
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.00015,
    "gpt-4o-mini-realtime-preview": 0.00015,
    "gpt-4o-realtime-preview": 0.005,
    "o1": 0.15,
    "o1-mini": 0.00015,
    "o1-pro": 0.15,
    "o3-mini": 0.00015,
    "o4-mini": 0.00015,
    "claude-3": 0.015,
    "gemini": 0.0005,
    "perplexity": 0.001,
    "perplexity-pro": 0.003,
    "perplexity-reasoning": 0.001,
    "perplexity-reasoning-pro": 0.002,
    "perplexity-deep-research": 0.002,
}

def load_runs(eval_dir: str):
    paths = sorted(glob.glob(os.path.join(eval_dir, "detailed_metrics_*.json")))
    runs = []
    for p in paths:
        try:
            with open(p, "r") as f:
                runs.append(json.load(f))
        except Exception:
            pass
    return runs

def avg(values):
    vals = [v for v in values if v is not None]
    return mean(vals) if vals else 0.0

def estimate_provider_costs(token_usage: dict):
    # Return estimated costs per provider family (OpenAI vs Perplexity) when possible
    openai_tokens = 0
    perplexity_tokens = 0
    other_tokens = 0
    for model, tokens in (token_usage or {}).items():
        if model is None:
            continue
        key = str(model).lower()
        if "perplexity" in key:
            perplexity_tokens += tokens
        elif any(k in key for k in ["gpt-4", "gpt-4o", "o1", "o3", "o4"]):
            openai_tokens += tokens
        else:
            other_tokens += tokens

    # Costs approximate using one representative price per family
    openai_cost = (openai_tokens / 1000.0) * PRICE_PER_1K.get("gpt-4o", 0.005)
    perplexity_cost = (perplexity_tokens / 1000.0) * PRICE_PER_1K.get("perplexity", 0.001)
    other_cost = (other_tokens / 1000.0) * 0.001
    return {
        "openai_tokens": openai_tokens,
        "perplexity_tokens": perplexity_tokens,
        "other_tokens": other_tokens,
        "openai_cost": openai_cost,
        "perplexity_cost": perplexity_cost,
        "other_cost": other_cost,
    }

def main():
    runs = load_runs(EVAL_DIR)
    n = len(runs)
    if n == 0:
        print("No evaluation results found.")
        return

    gen_times = [r.get("generation_time_seconds") for r in runs]
    total_costs = [r.get("total_cost_usd") for r in runs]
    fk_scores = [r.get("flesch_kincaid_score") for r in runs]
    analyst_scores = [r.get("analyst_readability_score") for r in runs]
    completeness_flags = [bool(r.get("all_sections_present")) for r in runs]
    cpu_list = [r.get("cpu_usage_percent") for r in runs]
    gpu_list = [r.get("gpu_usage_percent") for r in runs]
    mem_list = [r.get("memory_usage_mb") for r in runs]

    # Provider breakdown (rough estimate)
    openai_costs = []
    perplex_costs = []
    for r in runs:
        breakdown = estimate_provider_costs(r.get("token_usage", {}))
        openai_costs.append(breakdown["openai_cost"])
        perplex_costs.append(breakdown["perplexity_cost"])

    avg_time_sec = avg(gen_times)
    avg_time_min = avg_time_sec / 60.0
    avg_cost = avg(total_costs)
    avg_fk = avg(fk_scores)
    avg_analyst = avg(analyst_scores)
    completeness_rate = (sum(1 for x in completeness_flags if x) / n) * 100.0
    avg_cpu = avg(cpu_list)
    avg_gpu = avg(gpu_list)
    avg_mem = avg(mem_list)
    avg_openai_cost = avg(openai_costs)
    avg_perplex_cost = avg(perplex_costs)

    # 4-hour benchmark context
    four_hours_sec = 4 * 3600
    time_ratio = avg_time_sec / four_hours_sec if four_hours_sec else 0.0

    md = []
    md.append("# Aggregate Evaluation Summary")
    md.append("")
    md.append(f"- Runs aggregated: {n}")
    md.append(f"- Average time to memo: {avg_time_min:.1f} minutes (vs 4h benchmark: {time_ratio:.3f}x of 4h)")
    md.append(f"- Average total token cost: ${avg_cost:.4f}")
    md.append(f"  - Estimated OpenAI token cost portion: ${avg_openai_cost:.4f}")
    md.append(f"  - Estimated Perplexity token cost portion: ${avg_perplex_cost:.4f}")
    md.append("- CoreSignal pricing (not in token totals): $49/month for 250 downloads + 500 searches (~$0.196/credit)")
    md.append("")
    md.append(f"- Readability (Flesch–Kincaid): {avg_fk:.1f}")
    md.append(f"- Analyst readability (1–5): {avg_analyst:.2f}")
    md.append(f"- Section completeness (17/17 present): {completeness_rate:.1f}% of runs")
    md.append("")
    md.append(f"- Avg CPU usage: {avg_cpu:.1f}%")
    md.append(f"- Avg GPU usage: {avg_gpu:.1f}%")
    md.append(f"- Avg memory usage: {avg_mem:.1f} MB")

    out_path = os.path.join(EVAL_DIR, "aggregate_summary.md")
    with open(out_path, "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"\nSaved: {out_path}")

    # Also export a CSV with per-run key fields for appendix analysis
    csv_path = os.path.join(EVAL_DIR, "aggregate_runs.csv")
    fieldnames = [
        "file",
        "generation_time_seconds",
        "total_cost_usd",
        "flesch_kincaid_score",
        "analyst_readability_score",
        "all_sections_present",
        "cpu_usage_percent",
        "gpu_usage_percent",
        "memory_usage_mb",
    ]
    with open(csv_path, "w", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for p in sorted(glob.glob(os.path.join(EVAL_DIR, "detailed_metrics_*.json"))):
            try:
                with open(p, "r") as f:
                    r = json.load(f)
                writer.writerow({
                    "file": os.path.basename(p),
                    "generation_time_seconds": r.get("generation_time_seconds"),
                    "total_cost_usd": r.get("total_cost_usd"),
                    "flesch_kincaid_score": r.get("flesch_kincaid_score"),
                    "analyst_readability_score": r.get("analyst_readability_score"),
                    "all_sections_present": r.get("all_sections_present"),
                    "cpu_usage_percent": r.get("cpu_usage_percent"),
                    "gpu_usage_percent": r.get("gpu_usage_percent"),
                    "memory_usage_mb": r.get("memory_usage_mb"),
                })
            except Exception:
                continue
    print(f"Saved: {csv_path}")

if __name__ == "__main__":
    main()


