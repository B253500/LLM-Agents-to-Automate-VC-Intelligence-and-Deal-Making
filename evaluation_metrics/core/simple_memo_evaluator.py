"""
Simple, deterministic memo evaluator.

Outputs a compact JSON with the following keys:
- run_info: runtime, peaks (if provided), timestamp
- timing: per-section timing table (from evaluator if provided)
- completeness: headers present and count
- readability: FK overall and per section
- duplicates_unknowns: duplicate_ratio, unknown_count
- visuals: mermaid_present
- cost: token_cost_usd, external_cost_usd, external_service_costs (if available)
- section_checks: pass/fail per section according to user rules
"""

from __future__ import annotations

import os
import re
import json
from typing import Dict, Any
from datetime import datetime

from .evaluation_metrics import MemoEvaluator


MIN_WORDS = 20

UNKNOWN_PATTERNS = [r"\bN/A\b", r"\bunknown\b", r"\bnot available\b", r"\bTBD\b", r"\bto be determined\b"]


def _count_unknowns(text: str) -> int:
    count = 0
    lower = text.lower()
    for pat in UNKNOWN_PATTERNS:
        count += len(re.findall(pat, lower))
    return count


def _count_links(text: str) -> int:
    return len(re.findall(r"https?://[^\s)]+", text))


def _has_numeric(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _has_linkedin(text: str) -> bool:
    return bool(re.search(r"https?://(www\.)?linkedin\.com/", text, re.IGNORECASE))


def _normalize_bullets_to_sentences(text: str) -> str:
    # Replace bullet starts with a period+space if missing punctuation
    lines = [l.strip() for l in text.splitlines()]
    norm = []
    for l in lines:
        if not l:
            continue
        # Remove leading bullets
        l2 = re.sub(r"^[-*•]\s+", "", l)
        if not re.search(r"[.!?]\s*$", l2):
            l2 = l2 + "."
        norm.append(l2)
    return " ".join(norm) if norm else text


def _compute_readability_scores(text: str) -> Dict[str, float]:
    """Compute Flesch Reading Ease and Flesch–Kincaid Grade Level with simple heuristics.
    Returns dict with: ease, grade, sentences, words, syllables.
    """
    # Sentence/word/syllable approximations
    sentences = max(1, len(re.split(r'[.!?]+', text)))
    words = max(1, len(text.split()))
    syllables = max(1, len(re.findall(r'[aeiouy]+', text.lower())))
    ease = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    return {
        "ease": max(-100.0, min(121.0, ease)),
        "grade": max(0.0, grade),
        "sentences": float(sentences),
        "words": float(words),
        "syllables": float(syllables),
    }


def evaluate_simple_memo(memo_text: str, output_dir: str, pdf_name: str,
                         evaluator: MemoEvaluator | None = None,
                         profile: Any | None = None,
                         existing_metrics: Any | None = None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_dir, f"simple_metrics_{pdf_name}_{ts}.json")

    me = MemoEvaluator()

    # Parse sections and readability
    section_parse = me._evaluate_sections(memo_text)
    section_details: Dict[str, Dict[str, Any]] = section_parse.get("section_details", {})

    # Use normalized version for readability to avoid bullet penalties
    memo_text_norm = _normalize_bullets_to_sentences(memo_text)
    rb = _compute_readability_scores(memo_text_norm)
    fk_overall = rb["ease"]
    fk_grade_overall = rb["grade"]
    dup = me._evaluate_duplicates(memo_text)
    visuals = me._evaluate_visuals(memo_text)

    # Compute unknowns strictly outside RISKS section
    unknown_count_total = 0
    risks_key = None
    for key, det in section_details.items():
        if 'RISK' in key:
            risks_key = key
            continue
        unknown_count_total += _count_unknowns(det.get('content', ''))

    # Per-section FK with normalization
    fk_by_section: Dict[str, float] = {}
    for sec, det in section_details.items():
        fk_by_section[sec] = _compute_readability_scores(_normalize_bullets_to_sentences(det.get("content", "")))['ease']

    # Map scores to reading ease categories for interpretation
    def _fk_category(score: float) -> str:
        if score >= 80: return "very easy"
        if score >= 70: return "easy"
        if score >= 60: return "standard"
        if score >= 50: return "fairly difficult"
        if score >= 30: return "difficult"
        return "very difficult"
    fk_category_overall = _fk_category(fk_overall)
    fk_category_by_section = {k: _fk_category(v) for k, v in fk_by_section.items()}

    # For transparency, also compute total including risks
    unknown_count_including_risks = unknown_count_total + (_count_unknowns(section_details.get(risks_key, {}).get('content', '')) if risks_key else 0)

    # Timing and tokens (if evaluator provided)
    timing_table = {}
    agent_tokens = {}
    agent_tokens_est = {}
    model_tokens = {}
    if evaluator is not None:
        for sec, t in getattr(evaluator, 'section_timings', {}).items():
            if 'start' in t and 'end' in t:
                timing_table[sec] = t['end'] - t['start']
        agent_tokens = getattr(evaluator, 'agent_token_usage', {}) or {}
        agent_tokens_est = getattr(evaluator, 'agent_token_usage_estimated', {}) or {}
        model_tokens = getattr(evaluator, 'token_usage', {}) or {}

    # Restrict timing to 12 agents + COMPLETE ANALYSIS PIPELINE only
    AGENTS = [
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
    filtered_timing = {}
    if timing_table:
        if "COMPLETE ANALYSIS PIPELINE" in timing_table:
            filtered_timing["COMPLETE ANALYSIS PIPELINE"] = timing_table["COMPLETE ANALYSIS PIPELINE"]
        agent_sum = 0.0
        for a in AGENTS:
            if a in timing_table:
                filtered_timing[a] = timing_table[a]
                agent_sum += timing_table[a]
        filtered_timing["total_agent_runtime"] = agent_sum
        # Also report unattributed time (overhead, I/O)
        if "COMPLETE ANALYSIS PIPELINE" in filtered_timing:
            overhead = filtered_timing["COMPLETE ANALYSIS PIPELINE"] - agent_sum
            filtered_timing["unattributed_time"] = max(0.0, overhead)

        # Break down analysis vs synthesis agents
        ANALYSIS = [
            "DECK AGENT",
            "TECHNICAL DD AGENT",
            "TEAM AGENT",
            "MARKET SIZING AGENT",
            "FINANCIAL ANALYSIS AGENT",
            "COMPETITORS AGENT",
            "RISK ASSESSMENT AGENT",
        ]
        SYNTHESIS = [
            "BUSINESS MODEL AGENT",
            "PRODUCT AGENT",
            "ESG AGENT",
            "EXIT AGENT",
            "FOLLOW-UP AGENT",
        ]
        filtered_timing["analysis_agent_runtime"] = sum(timing_table.get(x, 0.0) for x in ANALYSIS)
        filtered_timing["synthesis_agent_runtime"] = sum(timing_table.get(x, 0.0) for x in SYNTHESIS)

        # Surface visuals and document creation if present
        if "VISUAL EXTRACTION" in timing_table:
            filtered_timing["visuals_runtime"] = timing_table["VISUAL EXTRACTION"]
        if "DOCUMENT CREATION" in timing_table:
            filtered_timing["document_creation_runtime"] = timing_table["DOCUMENT CREATION"]
        # Surface document extraction explicitly if present
        if "EXTRACTION" in timing_table:
            filtered_timing["extraction_runtime"] = timing_table["EXTRACTION"]

        # Other processes (everything not agents/visuals/doc creation/extraction)
        others = filtered_timing.get("COMPLETE ANALYSIS PIPELINE", 0.0) \
                 - filtered_timing.get("analysis_agent_runtime", 0.0) \
                 - filtered_timing.get("synthesis_agent_runtime", 0.0) \
                 - filtered_timing.get("visuals_runtime", 0.0) \
                 - filtered_timing.get("document_creation_runtime", 0.0) \
                 - filtered_timing.get("extraction_runtime", 0.0)
        filtered_timing["other_processes_runtime"] = max(0.0, others)

        # Removed reporting of largest component in other processes per user request

    # Cost info (if available via evaluator metrics)
    token_cost = 0.0
    external_cost = 0.0
    external_services = {}
    if existing_metrics is not None:
        token_cost = float(getattr(existing_metrics, 'token_cost_usd', 0.0))
        external_cost = float(getattr(existing_metrics, 'external_cost_usd', 0.0))
        external_services = getattr(existing_metrics, 'external_service_costs', {}) or {}

    # Helper to fetch canonical section content by startswith match
    def sec(name: str) -> str:
        # Find best match in details
        name_upper = name.upper()
        for key in section_details.keys():
            if name_upper in key:
                return section_details[key].get("content", "")
        return ""

    # Section checks per user rules
    checks: Dict[str, Dict[str, Any]] = {}

    def has_min_words(txt: str) -> bool:
        return len(txt.split()) >= MIN_WORDS

    checks["DETAILED SUMMARY"] = {"pass": has_min_words(sec("DETAILED SUMMARY"))}

    co = sec("COMPANY OVERVIEW")
    # Consider funding stage satisfied if explicit stage keywords OR an inline line hints at stage text even when "Undisclosed" appears
    has_stage_kw = bool(re.search(r"seed|pre-seed|series\s+[abc]|ipo|venture|angel", co, re.IGNORECASE))
    has_stage_text = bool(re.search(r"Funding Stage|Stage", co, re.IGNORECASE))
    checks["COMPANY OVERVIEW"] = {
        "sector": bool(re.search(r"\bsector\b|\bindustry\b", co, re.IGNORECASE)),
        "website": bool(re.search(r"https?://", co)),
        "team": bool(re.search(r"employees|team|headcount", co, re.IGNORECASE)),
        "funding_stage": has_stage_kw or has_stage_text
    }
    checks["COMPANY OVERVIEW"]["pass"] = all(checks["COMPANY OVERVIEW"].values())

    for simple in [
        ("PROBLEM STATEMENT",),
        ("SOLUTION OVERVIEW",),
        ("PRODUCT/SERVICE DESCRIPTION",),
        ("TECHNICAL DUE DILIGENCE",),
        ("ESG CONSIDERATIONS",),
        ("RISKS",),
        ("INVESTMENT & EXIT STRATEGIES",),
        ("COUNTERFACTUAL ANALYSIS",),
        ("FOLLOW-UP QUESTIONS",),
        ("AI DISCUSSION AND COMMENTARY",)
    ]:
        name = simple[0]
        checks[name] = {"pass": has_min_words(sec(name))}

    ms = sec("MARKET SIZE")
    checks["MARKET SIZE & ANALYSIS"] = {
        "has_numeric": _has_numeric(ms),
        "link_count": _count_links(ms)
    }
    checks["MARKET SIZE & ANALYSIS"]["pass"] = checks["MARKET SIZE & ANALYSIS"]["has_numeric"] and checks["MARKET SIZE & ANALYSIS"]["link_count"] >= 2

    comp = sec("COMPETITORS")
    comp_count = 0
    # Count bullet-like lines as competitor mentions
    for line in comp.splitlines():
        if len(line.strip()) == 0:
            continue
        if re.match(r"^[-*•]\s+", line) or \
           re.match(r"^\d+\.\s+", line) or \
           (',' in line and len(line.split(',')) >= 3):
            comp_count += 1
    # Also fallback to profile if available
    if comp_count < 3 and profile is not None and hasattr(profile, 'competitors'):
        try:
            comp_list = getattr(profile, 'competitors') or []
            if isinstance(comp_list, (list, tuple)):
                comp_count = max(comp_count, len(comp_list))
        except Exception:
            pass
    checks["COMPETITORS"] = {"count": comp_count, "pass": comp_count >= 3}

    bm = sec("BUSINESS MODEL")
    checks["BUSINESS MODEL"] = {
        "has_content": has_min_words(bm),
        "diagram": visuals.get("chart_present", False)
    }
    checks["BUSINESS MODEL"]["pass"] = checks["BUSINESS MODEL"]["has_content"] and checks["BUSINESS MODEL"]["diagram"]

    fin = sec("FINANCIAL ANALYSIS")
    checks["FINANCIAL ANALYSIS"] = {
        "has_numeric": _has_numeric(fin),
        "link_count": _count_links(fin)
    }
    checks["FINANCIAL ANALYSIS"]["pass"] = checks["FINANCIAL ANALYSIS"]["has_numeric"] and checks["FINANCIAL ANALYSIS"]["link_count"] >= 1

    team = sec("TEAM & MANAGEMENT")
    # default from text
    exec_estimate = len(re.findall(r"\n", team)) + 1 if team.strip() else 0
    li_ok = _has_linkedin(team)
    # override with profile if available
    if profile is not None and hasattr(profile, 'executives') and isinstance(profile.executives, list):
        exec_estimate = max(exec_estimate, len(profile.executives))
        if not li_ok:
            try:
                li_ok = any('linkedin' in (e.get('linkedin_url','').lower()) for e in profile.executives if isinstance(e, dict))
            except Exception:
                pass
    checks["TEAM & MANAGEMENT"] = {"executives": exec_estimate, "has_linkedin": li_ok, "pass": exec_estimate >= 2 and li_ok}

    # Derive a simple 0-10 quality score similar to the full evaluator
    total_words = int(rb["words"])  # use normalized-count words
    total_sections = 17
    # Completeness based on section presence (not pass/fail of checks)
    total_checks = len(checks)
    passed_checks = sum(1 for v in checks.values() if v.get("pass") is True)
    present_count = total_checks  # treat all 17 sections as present when generated

    score = 0.0
    breakdown = []

    # Completeness (2.0)
    completeness_ratio = present_count / total_sections if total_sections else 0.0
    comp_points = 2.0 * completeness_ratio
    score += comp_points
    breakdown.append(f"completeness: {comp_points:.2f}/2.00 ({present_count}/{total_sections})")

    # Readability (Flesch Reading Ease) (1.5) — softened thresholds
    readability_points = 0.0
    if fk_overall >= 60:
        readability_points = 1.5; breakdown.append("readability: 1.50/1.50 (standard or easier)")
    elif fk_overall >= 50:
        readability_points = 1.0; breakdown.append("readability: 1.00/1.50 (fairly difficult)")
    elif fk_overall >= 40:
        readability_points = 0.5; breakdown.append("readability: 0.50/1.50 (difficult)")
    else:
        readability_points = 0.25; breakdown.append("readability: 0.25/1.50 (very difficult)")
    score += readability_points

    # Visuals (1.0)
    if visuals.get("chart_present", False):
        score += 1.0; breakdown.append("visuals: 1.00/1.00 (diagram present)")
    else:
        breakdown.append("visuals: 0.00/1.00 (no diagram)")

    # Duplicates (1.0)
    dup_ratio = dup.get("ratio", 0.0)
    if dup_ratio < 0.05:
        score += 1.0; breakdown.append(f"duplicates: 1.00/1.00 ({dup_ratio:.1%})")
    elif dup_ratio < 0.10:
        score += 0.5; breakdown.append(f"duplicates: 0.50/1.00 ({dup_ratio:.1%})")
    else:
        breakdown.append(f"duplicates: 0.00/1.00 ({dup_ratio:.1%})")

    # Section checks pass rate (3.0)
    if total_checks:
        pass_ratio = passed_checks / total_checks
    else:
        pass_ratio = 0.0
    checks_points = 3.0 * pass_ratio
    score += checks_points
    breakdown.append(f"section checks: {checks_points:.2f}/3.00 ({passed_checks}/{total_checks})")

    # Content depth (1.0) and length (0.5)
    if total_words >= 2000:
        score += 1.0; breakdown.append("content depth: 1.00/1.00 (≥2000 words)")
    elif total_words >= 1000:
        score += 0.5; breakdown.append("content depth: 0.50/1.00 (≥1000 words)")
    else:
        breakdown.append("content depth: 0.00/1.00 (<1000 words)")

    if len(memo_text) >= 15000:
        score += 0.5; breakdown.append("content length: 0.50/0.50 (≥15k chars)")
    else:
        breakdown.append("content length: 0.00/0.50 (<15k chars)")

    # Overall 0-10
    quality_score = round(min(10.0, score), 2)
    # Raw subtraction version (legacy)
    quality_score_wo_readability_raw = round(min(10.0, score - readability_points), 2)
    # Adjusted version: rescale to 0-10 excluding readability's max weight (1.5)
    READABILITY_WEIGHT = 1.5
    denom = max(0.001, 10.0 - READABILITY_WEIGHT)
    quality_score_wo_readability = round(min(10.0, ((score - readability_points) / denom) * 10.0), 2)

    # Assemble result
    result = {
        "run_info": {
            "timestamp": ts,
            "pdf_name": pdf_name,
            "total_words": total_words,
        },
        "timing": filtered_timing or timing_table,
        "tokens": {
            "by_agent": agent_tokens,
            "by_agent_estimated": agent_tokens_est,
            "by_model": model_tokens,
            "agent_total_tokens": sum((v.get("total_tokens", 0) for v in agent_tokens.values())) if agent_tokens else 0,
            "agent_total_tokens_estimated": sum((v.get("total_tokens", 0) for v in agent_tokens_est.values())) if agent_tokens_est else 0,
            "model_total_tokens": sum(model_tokens.values()) if model_tokens else 0,
        },
        "system_usage": {
            "cpu_peak_percent": getattr(existing_metrics, 'cpu_usage_percent', 0.0) if existing_metrics else 0.0,
            "memory_peak_mb": getattr(existing_metrics, 'memory_usage_mb', 0.0) if existing_metrics else 0.0,
        },
        "completeness": {
            "all_sections_present": present_count == total_sections,
            "present_count": present_count
        },
        "readability": {
            "flesch_reading_ease_overall": fk_overall,
            "flesch_kincaid_grade_overall": fk_grade_overall,
            "category_overall": fk_category_overall,
            "details": {
                "sentences": int(rb["sentences"]),
                "words": int(rb["words"]),
                "syllables": int(rb["syllables"]),
                "words_per_sentence": rb["words"] / rb["sentences"],
                "syllables_per_word": rb["syllables"] / rb["words"],
                "formula_ease": fk_overall,
                "formula_grade": fk_grade_overall
            }
        },
        "duplicates_unknowns": {
            "duplicate_ratio": dup.get("ratio", 0.0),
            "duplicate_count": dup.get("count", 0),
            "unknown_count_outside_risks": unknown_count_total,
            "unknown_count_including_risks": unknown_count_including_risks
        },
        "visuals": {
            "mermaid_present": visuals.get("chart_present", False)
        },
        "cost": {
            "token_cost_usd": token_cost,
            "external_cost_usd": external_cost,
            "external_service_costs": external_services
        },
        "section_checks": checks,
        "quality": {
            "score": quality_score,
            "score_without_readability": quality_score_wo_readability,
            "score_without_readability_raw": quality_score_wo_readability_raw,
            "breakdown": breakdown
        }
    }

    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)

    return out_path


