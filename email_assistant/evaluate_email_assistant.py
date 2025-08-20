import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root on path so we can import agents
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.vc_report_agent import VCReportAgent  # noqa: E402


def load_dataset(path: Optional[str]) -> List[Dict[str, Any]]:
    if not path:
        # Fallback minimal dataset
        return [
            {"question": "Give me a market deep dive on UK insurtech trends in 2024, include CAGR.", "label": "market_deep_dive"},
            {"question": "Profile the founder 'Sam Altman' with education and key roles.", "label": "person"},
            {"question": "What do we know about the company Anthropic? revenue and latest funding?", "label": "company"},
            {"question": "Tell me about Sequoia Capital (fund) and its recent fundraising.", "label": "fund"},
        ]
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset not found: {p}")
    items: List[Dict[str, Any]] = []
    if p.suffix.lower() in {".jsonl", ".jl"}:
        with open(p, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))
    elif p.suffix.lower() == ".json":
        with open(p, "r") as f:
            payload = json.load(f)
            if isinstance(payload, list):
                items = payload
            else:
                raise ValueError("JSON dataset must be a list of objects")
    else:
        raise ValueError("Unsupported dataset format. Use .jsonl or .json")
    return items


def detect_numeric_claim(answer: str) -> bool:
    # Detect digits, percentages, or currency markers
    if not answer:
        return False
    patterns = [r"\$\s?\d", r"\d+%", r"\b\d{1,3}(?:[,\s]\d{3})+\b", r"\b\d+\b"]
    return any(re.search(p, answer) for p in patterns)


def citation_compliant(answer: str) -> bool:
    if not answer:
        return False
    return "(source:" in answer.lower() or "http" in answer.lower() or "coresignal" in answer.lower()


def compute_confusion_and_f1(labels: List[str], preds: List[str]) -> Tuple[Dict[Tuple[str, str], int], float]:
    assert len(labels) == len(preds)
    classes = sorted(set(labels) | set(preds))
    cm: Dict[Tuple[str, str], int] = defaultdict(int)
    per_class_f1: List[float] = []
    counts = {c: {"tp": 0, "fp": 0, "fn": 0} for c in classes}
    for y, yhat in zip(labels, preds):
        cm[(y, yhat)] += 1
        for c in classes:
            if y == c and yhat == c:
                counts[c]["tp"] += 1
            elif y != c and yhat == c:
                counts[c]["fp"] += 1
            elif y == c and yhat != c:
                counts[c]["fn"] += 1
    for c in classes:
        tp = counts[c]["tp"]
        fp = counts[c]["fp"]
        fn = counts[c]["fn"]
        if tp == 0 and (fp > 0 or fn > 0):
            per_class_f1.append(0.0)
            continue
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_class_f1.append(f1)
    macro_f1 = sum(per_class_f1) / len(per_class_f1) if per_class_f1 else 0.0
    return cm, macro_f1


def main():
    parser = argparse.ArgumentParser(description="Evaluate the Email Assistant without n8n.")
    parser.add_argument("--dataset", type=str, default=None, help="Path to .jsonl or .json with fields: question, label")
    parser.add_argument("--limit", type=int, default=0, help="Max examples to run (0=all)")
    parser.add_argument("--report", type=str, default="email_assistant_eval.json", help="Output metrics JSON path")
    parser.add_argument("--reports_dir", type=str, default="web_scraping/data/vc_reports", help="Reports root for local context")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set in environment.")
        sys.exit(1)

    data = load_dataset(args.dataset)
    if args.limit and args.limit > 0:
        data = data[: args.limit]

    agent = VCReportAgent(openai_api_key=api_key, report_path=args.reports_dir)

    gold_labels: List[str] = []
    pred_labels: List[str] = []
    latencies: List[float] = []
    numeric_with_citation: int = 0
    numeric_total: int = 0
    sources_present: int = 0
    errors: int = 0

    per_example: List[Dict[str, Any]] = []

    for idx, item in enumerate(data, start=1):
        q = item.get("question", "").strip()
        gold = item.get("label", "").strip()
        if not q or not gold:
            continue
        t0 = time.time()
        try:
            result = agent.analyze_question_enriched(q)
            dt = time.time() - t0
            latencies.append(dt)
            pred = result.get("classification", "")
            gold_labels.append(gold)
            pred_labels.append(pred)

            answer = result.get("answer", "")
            sources = result.get("sources", []) or []
            if detect_numeric_claim(answer):
                numeric_total += 1
                if citation_compliant(answer):
                    numeric_with_citation += 1
            if sources:
                sources_present += 1

            per_example.append(
                {
                    "question": q,
                    "gold_label": gold,
                    "pred_label": pred,
                    "latency_s": round(dt, 3),
                    "has_numeric": detect_numeric_claim(answer),
                    "citation_compliant": citation_compliant(answer),
                    "num_sources": len(sources),
                }
            )
            print(f"[{idx}/{len(data)}] gold={gold:>16} pred={pred:>16} latency={dt:.2f}s")
        except Exception as e:
            dt = time.time() - t0
            errors += 1
            latencies.append(dt)
            gold_labels.append(gold)
            pred_labels.append("<error>")
            per_example.append(
                {
                    "question": q,
                    "gold_label": gold,
                    "pred_label": "<error>",
                    "latency_s": round(dt, 3),
                    "error": str(e)[:500],
                }
            )
            print(f"[{idx}/{len(data)}] ERROR gold={gold} err={e}")

    # Metrics
    accuracy = sum(1 for g, p in zip(gold_labels, pred_labels) if g == p) / len(gold_labels) if gold_labels else 0.0
    cm, macro_f1 = compute_confusion_and_f1(gold_labels, pred_labels)
    p50 = statistics.median(latencies) if latencies else 0.0
    p90 = statistics.quantiles(latencies, n=10)[8] if len(latencies) >= 10 else (max(latencies) if latencies else 0.0)
    numeric_citation_rate = (numeric_with_citation / numeric_total) if numeric_total > 0 else None
    sources_rate = (sources_present / len(per_example)) if per_example else 0.0

    # Prepare confusion matrix readable dict
    cm_dict: Dict[str, Dict[str, int]] = defaultdict(dict)
    for (gold, pred), cnt in cm.items():
        cm_dict[gold][pred] = cnt

    report = {
        "total": len(per_example),
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "latency_s": {"p50": round(p50, 3), "p90": round(p90, 3)},
        "error_count": errors,
        "numeric_claims": {"total": numeric_total, "with_citation": numeric_with_citation, "rate": (round(numeric_citation_rate, 4) if numeric_citation_rate is not None else None)},
        "sources_presence_rate": round(sources_rate, 4),
        "confusion_matrix": cm_dict,
        "examples": per_example,
    }

    out_path = Path(args.report)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved evaluation report to {out_path.resolve()}")


if __name__ == "__main__":
    main()


