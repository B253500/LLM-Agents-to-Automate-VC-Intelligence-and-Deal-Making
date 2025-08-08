import json
import os
from pathlib import Path
from typing import List, Dict, Any
import argparse

import fitz  # PyMuPDF
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdf2image import convert_from_path
import pytesseract


ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = ROOT / "web_scraping" / "data" / "vc_reports"
OUT_DIR = REPORTS_ROOT / "cached_market_data"


def gather_pdfs(only_test_sample: bool = False) -> List[Path]:
    candidates: List[Path] = []
    roots = [REPORTS_ROOT / "test_sample"] if only_test_sample else [REPORTS_ROOT / "test_sample", REPORTS_ROOT]
    seen = set()
    for r in roots:
        if not r.exists():
            continue
        for p in r.rglob("*.pdf"):
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            candidates.append(p)
    return candidates


def _ocr_page(pdf_path: Path, page_index_one_based: int, dpi: int = 200, max_chars_per_page: int = 4000) -> str:
    try:
        images = convert_from_path(
            str(pdf_path), dpi=dpi, first_page=page_index_one_based, last_page=page_index_one_based
        )
        text_parts: List[str] = []
        for img in images:
            try:
                t = (pytesseract.image_to_string(img) or "").strip()
                if t:
                    text_parts.append(t)
            except Exception:
                continue
        joined = "\n".join(text_parts).strip()
        return joined[:max_chars_per_page] if joined else ""
    except Exception:
        return ""


def extract_pages_with_fallback(pdf_path: Path, max_chars_per_page: int = 4000, min_chars: int = 30) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    # Try PyMuPDF per page, OCR fallback for weak pages
    try:
        with fitz.open(str(pdf_path)) as doc:
            for idx in range(doc.page_count):
                page = doc.load_page(idx)
                text = (page.get_text("text") or "").strip()
                if len(text) < min_chars:
                    text = _ocr_page(pdf_path, idx + 1, dpi=200, max_chars_per_page=max_chars_per_page)
                if text:
                    pages.append({
                        "page": idx + 1,
                        "text": text[:max_chars_per_page]
                    })
        return pages
    except Exception:
        pass

    # Fallback to pdfplumber
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, pg in enumerate(pdf.pages, start=1):
                try:
                    text = (pg.extract_text() or "").strip()
                    if len(text) < min_chars:
                        text = _ocr_page(pdf_path, idx, dpi=200, max_chars_per_page=max_chars_per_page)
                    if text:
                        pages.append({
                            "page": idx,
                            "text": text[:max_chars_per_page]
                        })
                except Exception:
                    continue
        if pages:
            return pages
    except Exception:
        pass

    # Fallback to pdfminer (whole file)
    try:
        text = (pdfminer_extract_text(str(pdf_path)) or "").strip()
        if text:
            pages.append({
                "page": 1,
                "text": text[:max_chars_per_page]
            })
    except Exception:
        pass
    return pages


def extract_tables_with_pdfplumber(pdf_path: Path, max_cells: int = 5000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, pg in enumerate(pdf.pages, start=1):
                try:
                    tables = pg.extract_tables() or []
                    for t_idx, table in enumerate(tables, start=1):
                        rows = []
                        cell_count = 0
                        for row in table:
                            clean = [(c or "").strip() for c in row]
                            rows.append(clean)
                            cell_count += len(clean)
                            if cell_count >= max_cells:
                                break
                        out.append({
                            "page": idx,
                            "table_index": t_idx,
                            "rows": rows,
                        })
                except Exception:
                    continue
    except Exception:
        pass
    return out


def build_cache(only_test_sample: bool = False) -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index: Dict[str, Any] = {"files": []}

    for pdf_path in gather_pdfs(only_test_sample=only_test_sample):
        rel = pdf_path.relative_to(REPORTS_ROOT)
        print(f"Processing {rel}")
        pages = extract_pages_with_fallback(pdf_path)
        tables = extract_tables_with_pdfplumber(pdf_path)

        payload = {
            "file": pdf_path.name,
            "relative_path": str(rel),
            "pages": pages,
            "tables": tables,
        }

        out_file = OUT_DIR / f"{pdf_path.stem}.json"
        with open(out_file, "w") as f:
            json.dump(payload, f)

        index["files"].append({
            "file": pdf_path.name,
            "relative_path": str(rel),
            "json": out_file.name,
            "num_pages": len(pages),
            "num_tables": len(tables),
        })

    with open(OUT_DIR / "index.json", "w") as f:
        json.dump(index, f)

    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build cached market data from PDFs")
    parser.add_argument("--only-test-sample", action="store_true", help="Limit to web_scraping/data/vc_reports/test_sample only")
    args = parser.parse_args()

    idx = build_cache(only_test_sample=args.only_test_sample)
    print(f"Wrote cache for {len(idx['files'])} PDFs to {OUT_DIR}")

