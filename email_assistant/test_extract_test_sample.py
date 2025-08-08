import os
import json
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract_text

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from pdf2image import convert_from_path
import pytesseract
import re


ROOT = Path(__file__).resolve().parents[1]
TEST_SAMPLE_DIR = ROOT / "web_scraping" / "data" / "vc_reports" / "test_sample"
TEMP_CHROMA_DIR = ROOT / "tmp" / "test_sample_chroma"
OUT_DIR = ROOT / "web_scraping" / "data" / "vc_reports" / "cached_market_data_test"


QUESTIONS = [
    "What’s the current deal activity size for Insurtech in the most recent financial quarter?",
    "What’s the total value of exits in the biotechnology/bio tools space in Q1 2025?",
    "What are the top 3 academic institutions by spin out activity in the UK?",
    "How many companies do they spin out on average individually?",
    "What is the top sector of UK academic spinouts?",
    "What’s the top sub-sector of Quantum Computing by number of companies generated?",
    "What’s the CAGR of median gaming early-stage VC deal value and pre-money valuation ($M) in the segment of development?",
]


def ocr_page(pdf_path: Path, page_index_one_based: int, dpi: int = 200, min_chars: int = 30) -> List[Document]:
    try:
        images = convert_from_path(
            str(pdf_path), dpi=dpi, first_page=page_index_one_based, last_page=page_index_one_based
        )
        docs: List[Document] = []
        for img in images:
            try:
                text = (pytesseract.image_to_string(img) or "").strip()
                if len(text) >= min_chars:
                    docs.append(Document(page_content=text, metadata={
                        "source": pdf_path.name,
                        "page": page_index_one_based,
                        "type": "ocr_text"
                    }))
            except Exception:
                continue
        return docs
    except Exception:
        return []


def extract_pages(pdf_path: Path, min_chars: int = 30) -> List[Document]:
    docs: List[Document] = []
    # Try PyMuPDF per page
    try:
        with fitz.open(str(pdf_path)) as doc:
            for idx in range(doc.page_count):
                page = doc.load_page(idx)
                text = (page.get_text("text") or "").strip()
                if len(text) >= min_chars:
                    docs.append(Document(page_content=text, metadata={"source": pdf_path.name, "page": idx + 1}))
                else:
                    # Try OCR for figures/graphs-heavy pages
                    docs.extend(ocr_page(pdf_path, idx + 1, min_chars=min_chars))
        return docs
    except Exception:
        pass

    # Fallback to pdfplumber per page
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, pg in enumerate(pdf.pages, start=1):
                text = (pg.extract_text() or "").strip()
                if len(text) >= min_chars:
                    docs.append(Document(page_content=text, metadata={"source": pdf_path.name, "page": idx}))
                else:
                    docs.extend(ocr_page(pdf_path, idx, min_chars=min_chars))
        if docs:
            return docs
    except Exception:
        pass

    # pdfminer whole file as last resort
    try:
        text = (pdfminer_extract_text(str(pdf_path)) or "").strip()
        if len(text) >= min_chars:
            docs.append(Document(page_content=text, metadata={"source": pdf_path.name, "page": 1}))
    except Exception:
        pass
    return docs


def extract_tables(pdf_path: Path, max_cells: int = 5000) -> List[Document]:
    out: List[Document] = []
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
                        # Convert to CSV-like lines for retrieval friendliness
                        lines = [", ".join(r) for r in rows]
                        txt = ("\n".join(lines)).strip()
                        if txt:
                            out.append(Document(page_content=f"Table (p{idx} t{t_idx})\n{txt}", metadata={
                                "source": pdf_path.name,
                                "page": idx,
                                "type": "table"
                            }))
                except Exception:
                    continue
    except Exception:
        pass
    return out


def build_test_index(embeddings: OpenAIEmbeddings) -> Chroma:
    TEMP_CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    documents: List[Document] = []
    for pdf in TEST_SAMPLE_DIR.glob("*.pdf"):
        documents.extend(extract_pages(pdf))
        documents.extend(extract_tables(pdf))

    if not documents:
        raise SystemExit(f"No documents extracted from {TEST_SAMPLE_DIR}")

    # Create vector store fresh for test
    if TEMP_CHROMA_DIR.exists():
        # ensure a clean slate
        for p in TEMP_CHROMA_DIR.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    vector_store = Chroma.from_documents(documents=documents, embedding=embeddings, persist_directory=str(TEMP_CHROMA_DIR))
    return vector_store


def llm_answer_with_snippets(llm: ChatOpenAI, question: str, docs: List[Document]) -> str:
    context = "\n\n---\n\n".join([f"[Source: {d.metadata.get('source')}, Page {d.metadata.get('page')}]\n{d.page_content}" for d in docs])
    prompt = (
        "You are a VC research assistant. Use ONLY the following snippets from local reports to answer the question.\n"
        "If the snippets don't contain enough information, say that explicitly.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    )
    resp = llm.invoke(prompt)
    return getattr(resp, "content", str(resp))


def _to_number(token: str) -> float | None:
    t = token.strip().lower().replace(",", "")
    try:
        mult = 1.0
        if t.endswith("bn") or t.endswith("b"):
            mult = 1_000_000_000.0
            t = t.rstrip("bn").rstrip("b")
        elif t.endswith("m"):
            mult = 1_000_000.0
            t = t.rstrip("m")
        elif t.endswith("k"):
            mult = 1_000.0
            t = t.rstrip("k")
        if t.startswith("$"):
            t = t[1:]
        val = float(t)
        return val * mult
    except Exception:
        return None


def compute_average_spinouts_from_docs(docs: List[Document]) -> dict | None:
    # Parse lines/tables for university rows and numeric counts; avoid years
    uni_pat = re.compile(r"(University of [A-Za-z][A-Za-z&\-\s]+|Imperial College London|University College London)")
    year_set = set(range(2000, 2031))
    candidates: list[tuple[str, int, str, int | None, str]] = []  # name, count, source, page, line
    for d in docs:
        text = d.page_content
        for line in text.splitlines():
            m = uni_pat.search(line)
            if not m:
                continue
            nums = [int(n) for n in re.findall(r"\b(\d{1,4})\b", line)]
            # filter plausible counts
            plausible = [n for n in nums if n not in year_set and 5 <= n <= 1000]
            if not plausible:
                continue
            count = max(plausible)
            name = m.group(1).strip()
            candidates.append((name, count, d.metadata.get("source", "unknown"), d.metadata.get("page"), line.strip()))
    if not candidates:
        return None
    # Deduplicate by university, keep highest count seen
    best: dict[str, tuple[int, str, int | None, str]] = {}
    for name, count, src, page, line in candidates:
        if name not in best or count > best[name][0]:
            best[name] = (count, src, page, line)
    # Take top 3
    top_items = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)[:3]
    avg = sum(v[0] for _, v in top_items) / len(top_items)
    cites = [{"university": name, "count": v[0], "source": v[1], "page": v[2], "evidence": v[3]} for name, v in top_items]
    return {"average": avg, "top_sample": cites}


def compute_cagr_from_docs(docs: List[Document], value_keywords: list[str]) -> dict | None:
    # Try to collect (year, value) pairs from lines containing keywords
    year_val: dict[int, float] = {}
    year_pat = re.compile(r"\b(20\d{2})\b")
    money_pat = re.compile(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?\s*(?:[KkMmBb]|bn)?|\$\s*[0-9]+(?:\.[0-9]+)?\s*(?:[KkMmBb]|bn)?)")
    for d in docs:
        text = d.page_content
        lower = text.lower()
        if not all(k in lower for k in value_keywords):
            continue
        # inspect by lines
        for line in text.splitlines():
            line_l = line.lower()
            if not any(k in line_l for k in value_keywords):
                continue
            years = [int(y) for y in year_pat.findall(line)]
            monies = [m.group(1) for m in money_pat.finditer(line)]
            # Map nearest year to first value on the line
            if years and monies:
                val_num = None
                for token in monies:
                    val_num = _to_number(token)
                    if val_num is not None:
                        break
                if val_num is None:
                    continue
                for y in years:
                    # keep first occurrence per year
                    if y not in year_val:
                        year_val[y] = val_num
    if len(year_val) < 2:
        return None
    years_sorted = sorted(year_val.keys())
    first_y, last_y = years_sorted[0], years_sorted[-1]
    n = last_y - first_y
    if n <= 0:
        return None
    first_v, last_v = year_val[first_y], year_val[last_y]
    try:
        cagr = (last_v / first_v) ** (1.0 / n) - 1.0
    except Exception:
        return None
    series = [{"year": y, "value": year_val[y]} for y in years_sorted]
    return {"cagr": cagr, "first_year": first_y, "last_year": last_y, "series": series}


def main():
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in .env")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    llm = ChatOpenAI(temperature=0, model="gpt-4o", openai_api_key=api_key)

    print("Building test-only RAG index from test_sample …")
    vs = build_test_index(embeddings)

    results: Dict[str, Any] = {}
    for q in QUESTIONS:
        print(f"Query: {q}")
        # Retrieve top-k chunks
        retrieved = vs.similarity_search(q, k=20)
        answer = llm_answer_with_snippets(llm, q, retrieved)
        # Collect sources unique
        seen = set()
        sources = []
        for d in retrieved:
            src = d.metadata.get("source", "Unknown")
            page = d.metadata.get("page")
            key = (src, page)
            if key in seen:
                continue
            seen.add(key)
            sources.append({"source": src, "page": page})

        extra: Dict[str, Any] = {}
        ql = q.lower()
        if "average" in ql and "spin out" in ql:
            avg = compute_average_spinouts_from_docs(retrieved)
            if avg:
                extra["computed_average_spinouts"] = avg
        if "cagr" in ql and "gaming" in ql:
            # try for deal value
            calc_deal = compute_cagr_from_docs(
                retrieved,
                ["gaming", "median", "deal", "value", "development"],
            )
            # try for pre-money
            calc_pre = compute_cagr_from_docs(
                retrieved,
                ["gaming", "pre-money", "valuation", "development"],
            )
            if calc_deal or calc_pre:
                extra["computed_cagr"] = {"deal_value": calc_deal, "pre_money": calc_pre}

        results[q] = {
            "answer": answer,
            "sources": sources,
            **({"computed": extra} if extra else {}),
        }

    out_path = OUT_DIR / "answers.json"
    with open(out_path, "w") as f:
        json.dump(results, f)
    print(f"Wrote test answers to {out_path}")


if __name__ == "__main__":
    main()

