from typing import List, Dict, Optional, Any, Set
import os
from pathlib import Path
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.chains.llm import LLMChain
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
import json
import logging
import time
import re
# Optional reranker dependency
try:
    from sentence_transformers import CrossEncoder  # type: ignore
except Exception:
    CrossEncoder = None  # Graceful fallback when not installed
import pdfplumber
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdf2image import convert_from_path
import pytesseract

# Set up logging
logger = logging.getLogger(__name__)

# Add RerankerAgent class
class RerankerAgent:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = None
        self.available = False
        if CrossEncoder is not None:
            try:
                self.model = CrossEncoder(model_name)
                self.available = True
            except Exception:
                # If model load fails (e.g., torch not installed), continue without reranker
                self.model = None
                self.available = False

    def rerank(self, question: str, docs, top_k: int = 4):
        if not self.available or self.model is None or not docs:
            # Fallback: return first top_k documents unchanged
            return docs[:top_k]
        pairs = [[question, doc.page_content] for doc in docs]
        scores = self.model.predict(pairs)
        reranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in reranked[:top_k]]

class VCReportAgent:
    def __init__(self, openai_api_key: str, report_path: str):
        """Initialize the VC Report Agent."""
        self.reports_dir = Path(report_path)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.vector_store = None
        self.qa_chain = None
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o", openai_api_key=openai_api_key)
        self.reranker = RerankerAgent()  # Add reranker
        self.rag_available = False
        # self._initialize_agent() # RAG is fully disabled.

        # Lazy imports for optional enrichers (avoid hard dependency issues at import time)
        try:
            from core.coresignal_utils import get_full_company_data  # noqa: F401
            from core.external_enrichment import get_linkedin_profile_proxycurl  # noqa: F401
            from core.perplexity_utils import search_perplexity  # noqa: F401
            self._enrichment_available = True
        except Exception:
            # Enrichment is optional; base RAG will still function
            self._enrichment_available = False

    def _normalize_domain(self, url: str) -> str:
        try:
            if not url:
                return ""
            u = url.strip()
            if u.startswith("http"):
                # strip protocol
                u = u.split("//", 1)[-1]
            # strip path
            u = u.split("/", 1)[0]
            # strip query
            u = u.split("?", 1)[0]
            # strip www
            if u.startswith("www."):
                u = u[4:]
            return u.lower()
        except Exception:
            return ""

    def _extract_domain_from_text(self, text: str) -> str:
        try:
            if not text:
                return ""
            import re as _re
            m = _re.search(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)+)\b", text.lower())
            if not m:
                return ""
            domain = m.group(1)
            # blacklist common non-official domains
            blacklist = {"linkedin.com", "x.com", "twitter.com", "facebook.com", "wikipedia.org", "crunchbase.com"}
            if domain in blacklist:
                return ""
            return domain
        except Exception:
            return ""

    def _perplexity_get_company_hints(self, name: str) -> Dict[str, str]:
        """Use Perplexity to fetch LinkedIn company URL and official website domain."""
        hints: Dict[str, str] = {}
        if not self._enrichment_available:
            return hints
        try:
            from core.perplexity_utils import search_perplexity as _pplx
            # LinkedIn company URL
            li_res = _pplx(f"site:linkedin.com/company {name}", return_url=True, max_tokens=128)
            if isinstance(li_res, dict):
                li_url = li_res.get("url") or ""
                if li_url and "linkedin.com/company" in li_url:
                    hints["linkedin_url"] = li_url
            # Gather domain candidates
            domain_candidates: list[str] = []
            # Ask directly for official domain
            dom_res = _pplx(
                f"What is the official website domain for {name}? Respond with only the domain (e.g., 'stripe.com').",
                return_url=False,
                max_tokens=32,
                temperature=0.0,
            )
            if isinstance(dom_res, str):
                d = self._extract_domain_from_text(dom_res.strip())
                if d:
                    domain_candidates.append(d)
            # If LinkedIn URL is known, ask for the website linked on that page
            li_url = hints.get("linkedin_url")
            if li_url:
                dom_from_li = _pplx(
                    f"From the LinkedIn company page {li_url}, what is the official website domain? Answer with domain only (e.g., 'stripe.com').",
                    return_url=False,
                    max_tokens=32,
                    temperature=0.0,
                )
                if isinstance(dom_from_li, str):
                    d2 = self._extract_domain_from_text(dom_from_li.strip())
                    if d2:
                        domain_candidates.append(d2)
            # Fallback phrasing
            if not domain_candidates:
                dom_res2 = _pplx(
                    f"official website domain of {name}. Answer with domain only",
                    return_url=False,
                    max_tokens=32,
                    temperature=0.0,
                )
                if isinstance(dom_res2, str):
                    d3 = self._extract_domain_from_text(dom_res2.strip())
                    if d3:
                        domain_candidates.append(d3)
            # Select best domain against company name
            best = self._select_best_domain(name, domain_candidates)
            if best:
                hints["website_domain"] = best
        except Exception:
            pass
        return hints

    def _select_best_domain(self, name: str, domains: list[str]) -> str:
        if not domains:
            return ""
        # Remove obvious social/non-officials and duplicates
        blacklist = {"linkedin.com", "x.com", "twitter.com", "facebook.com", "wikipedia.org", "crunchbase.com"}
        cand = [d for d in domains if d and d not in blacklist]
        if not cand:
            return ""
        # Prefer domain that contains normalized name token
        token = re.sub(r"[^a-z]", "", name.lower())
        scored: list[tuple[int, str]] = []
        for d in cand:
            dn = d.lower()
            score = 0
            if token and token in dn:
                score += 5
            # shorter is usually better
            score += max(0, 20 - len(dn))
            scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else ""

    def _extract_keywords(self, question: str) -> Set[str]:
        """Extract relevant keywords from the question."""
        # Common VC and sector terms
        vc_terms = {'deal', 'exit', 'valuation', 'funding', 'investment', 'round', 'series', 
                   'pre-money', 'post-money', 'cagr', 'growth', 'quarter', 'annual', 'year'}
        
        # Sector-specific terms
        sector_terms = {'insurtech', 'biotech', 'gaming', 'quantum', 'ai', 'artificial intelligence',
                       'healthcare', 'fintech', 'enterprise', 'consumer', 'hardware', 'software'}
        
        # Extract words from question
        words = set(re.findall(r'\b\w+\b', question.lower()))
        
        # Combine with relevant terms
        keywords = words.union(vc_terms.intersection(words))
        keywords = keywords.union(sector_terms.intersection(words))
        
        # Add temporal terms if present
        if any(year in question for year in ['2020', '2021', '2022', '2023', '2024', '2025']):
            keywords.add('temporal')
        
        return keywords

    def _get_relevant_documents(self, question: str, k: int = 10) -> List[Any]:
        """Get relevant documents using both semantic and keyword search, then rerank."""
        if not self.rag_available or self.vector_store is None:
            return []
        keywords = self._extract_keywords(question)
        # Always retrieve more for reranking
        k_retrieve = max(10, k)
        semantic_docs = self.vector_store.similarity_search(question, k=k_retrieve)
        keyword_docs = []
        if keywords:
            for keyword in keywords:
                try:
                    docs = self.vector_store.similarity_search(keyword, k=2)
                    keyword_docs.extend(docs)
                except Exception as e:
                    logger.warning(f"Error searching for keyword {keyword}: {str(e)}")
        if 'cagr' in question.lower():
            try:
                year_docs = self.vector_store.similarity_search("2020 2021 2022 2023 2024 2025", k=3)
                keyword_docs.extend(year_docs)
            except Exception as e:
                logger.warning(f"Error searching for temporal data: {str(e)}")
        all_docs = semantic_docs + keyword_docs
        seen_content = set()
        unique_docs = []
        for doc in all_docs:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_docs.append(doc)
        # Rerank and select top k (graceful fallback if reranker unavailable)
        top_docs = self.reranker.rerank(question, unique_docs, top_k=4)
        # Debug: print top chunks (reranked or original depending on availability)
        print("\n\n--- Top Chunks for Debug (post-rerank if available) ---\n")
        for i, doc in enumerate(top_docs):
            print(f"Chunk {i+1} (first 500 chars):\n{doc.page_content[:500]}\n")
        return top_docs

    def _initialize_agent(self):
        """
        Initializes the agent by loading the persistent ChromaDB vector store.
        It no longer builds the database; that is handled by the ingestion script.
        """
        db_path = "./chroma_db"
        try:
            if not os.path.exists(db_path) or not os.listdir(db_path):
                logger.warning(
                    f"ChromaDB not found at {db_path}. Proceeding without RAG; answers will not cite local sources."
                )
                self.vector_store = None
                self.rag_available = False
            else:
                logger.info(f"Loading existing vector store from: {db_path}")
                self.vector_store = Chroma(
                    persist_directory=db_path,
                    embedding_function=self.embeddings
                )
                self.rag_available = True
        except Exception as e:
            logger.warning(f"Failed to load vector store: {e}. Disabling RAG.")
            self.vector_store = None
            self.rag_available = False

        # Create the QA chain
        def create_qa_chain():
            def qa_with_context(input_dict):
                question = input_dict["query"]
                docs = self._get_relevant_documents(question, k=4)
                context = "\n\n".join([doc.page_content for doc in docs])
                
                full_prompt = f"""You are a VC report analysis expert. Use the following context to answer the question.

For CAGR (Compound Annual Growth Rate) calculations:
- Find the beginning and ending values from the context
- Calculate: CAGR = (Ending Value / Beginning Value)^(1/number of years) - 1
- Show your calculation step by step
- Convert the result to a percentage

Important: 
1. Use specific numbers and data points from the context
2. If you find conflicting information, explain the conflict
3. If you're unsure about any part, explicitly state what you're uncertain about
4. For calculations, show your work step by step in plain text
5. NEVER use LaTeX math formulas
6. Use simple text format for all math: "CAGR = (Ending Value / Beginning Value)^(1/n) - 1"
7. For fractions, use "X divided by Y" or "X/Y"
8. For exponents, use "X to the power of Y" or "X^Y"
9. For averages, use "Average = (A + B + C) / 3"
10. Make all mathematical expressions human-readable in plain text
11. Always perform the actual calculations when asked for CAGR, percentages, or other math
12. If you find data for different time periods, calculate CAGR for each period mentioned
        
        Context: {context}
        
        Question: {question}
        
Answer:"""
                
                response = self.llm.invoke(full_prompt)
                return {"result": response.content}
            
            return qa_with_context
        
        self.qa_chain = create_qa_chain()

    def _clean_math_formulas(self, text: str) -> str:
        """Convert LaTeX math formulas to human-readable text."""
        import re
        
        # Replace LaTeX fractions
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 divided by \2', text)
        
        # Replace LaTeX text commands
        text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
        
        # Replace LaTeX brackets
        text = re.sub(r'\\\[', '', text)
        text = re.sub(r'\\\]', '', text)
        
        # Replace LaTeX parentheses
        text = re.sub(r'\\left\(', '(', text)
        text = re.sub(r'\\right\)', ')', text)
        
        # Replace LaTeX exponents
        text = re.sub(r'\^\{([^}]+)\}', r' to the power of \1', text)
        
        # Clean up any remaining LaTeX commands
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def analyze_question(self, question: str, provided_docs: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Analyze a question with optional RAG. Falls back to LLM-only if RAG is unavailable or fails."""
        try:
            with get_openai_callback() as cb:
                rag_used = False
                docs: List[Any] = []
                try:
                    docs = self._get_relevant_documents(question, k=8)
                    rag_used = len(docs) > 0
                except Exception as re:
                    logger.warning(f"RAG retrieval failed: {re}. Continuing without context.")
                    docs = []
                    rag_used = False

                context = "\n\n".join([doc.page_content for doc in docs]) if docs else ""
                if context:
                    full_prompt = f"You are a VC report analysis expert. Use the following context to answer the question.\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
                else:
                    full_prompt = (
                        "You are a VC report analysis expert. There is no local context available. "
                        "Answer concisely using general knowledge; if data is missing, say so and suggest what report section to consult.\n\n"
                        f"Question: {question}\n\nAnswer:"
                    )

                response = self.llm.invoke(full_prompt)
                cleaned_answer = self._clean_math_formulas(getattr(response, "content", str(response)))

                temporal_valid = self._validate_temporal_context(question, docs) if docs else True
                seen_sources: Set[str] = set()
                sources: List[Dict[str, Any]] = []
                for doc in docs:
                    source = doc.metadata.get("source", "Unknown")
                    if source not in seen_sources:
                        seen_sources.add(source)
                        meta = {
                            "source": source,
                            "has_visual": doc.metadata.get("has_visual", False),
                            "temporal_valid": temporal_valid,
                        }
                        if "page" in doc.metadata:
                            meta["page"] = doc.metadata["page"]
                        sources.append(meta)

                return {
                    "answer": cleaned_answer,
                    "sources": sources,
                    "rag_used": rag_used,
                    "validation": {
                        "temporal_valid": temporal_valid,
                        "tokens_used": cb.total_tokens,
                        "cost": cb.total_cost,
                        "keywords_searched": list(self._extract_keywords(question)),
                    },
                }
        except Exception as e:
            logger.error(f"Error analyzing question: {str(e)}")
            return {
                "answer": f"Error analyzing question: {str(e)}",
                "sources": [],
                "rag_used": False,
                "validation": {
                    "temporal_valid": False,
                    "tokens_used": 0,
                    "cost": 0.0,
                    "keywords_searched": [],
                },
            }

    # ===== Enriched, Task-Aware Analysis (optional) =====
    def classify_task(self, question: str) -> str:
        """Heuristic classifier with safer person detection and prioritized market cues."""
        q = question.lower()
        # Explicit person cues only; avoid ambiguous tokens like 'bio' which collides with 'bio tools'.
        person_terms = [
            "person", "profile", "linkedin", "linkedin.com", "who is", "biography",
            "about", "resume", "cv", "education", "background"
        ]
        fund_terms = ["fund", "vc fund", "venture fund", "capital", "investment firm"]
        company_terms = ["company", "website", "employees", "headcount", "revenue", "customers"]

        market_terms = [
            "deep dive", "market", "segment", "tam", "sam", "som", "market size", "industry",
            "trend", "trends", "vc trends", "deal activity", "vc deals", "early-stage", "early stage",
            "cagr", "exits", "exit", "valuation", "median", "pre-money", "post-money", "survey",
            "snapshot", "analyst note", "benchmarks", "benchmark", "outlook", "state of", "report",
            "sub-sector", "subsector", "ecosystem", "spinout", "spin-out", "spin out"
        ]
        sector_terms = [
            "biotech", "bio tools", "biotools", "gaming", "insurtech", "quantum", "e-commerce", "ecommerce",
            "foodtech", "pharma", "healthcare", "fintech", "clean energy", "deep tech", "life sciences"
        ]

        has_quarter = bool(re.search(r"\bq\s*[1-4]\s*20\d{2}\b|\bq[1-4]_?20\d{2}\b", q))

        # PRIORITIZE market cues before person to avoid false positives like 'bio tools'
        if any(t in q for t in market_terms) or has_quarter or any(t in q for t in sector_terms):
            return "market_deep_dive"

        if any(t in q for t in fund_terms):
            return "fund"
        if any(t in q for t in company_terms):
            return "company"

        # Person detection only on explicit cues (no capitalization heuristic)
        if any(t in q for t in person_terms):
            return "person"

        return "generic"

    def _extract_candidate_name_or_company(self, question: str) -> str:
        """Naive extractor: try quoted text first, else return longest Capitalized phrase."""
        import re
        # quoted content
        m = re.search(r'"([^"]+)"|\'([^\']+)\'', question)
        if m:
            return (m.group(1) or m.group(2) or "").strip()

        # capitalized words sequences (simple heuristic)
        tokens = re.findall(r"[A-Z][a-zA-Z]+", question)
        if tokens:
            return " ".join(tokens[:3]).strip()
        return ""

    def enrich_with_coresignal(self, question: str) -> Dict[str, Any]:
        """Fetch company/fund data via CoreSignal if available."""
        if not self._enrichment_available:
            return {"available": False, "reason": "enrichment deps missing"}
        try:
            from core.coresignal_utils import get_full_company_data
            name = self._extract_candidate_name_or_company(question)
            if not name:
                return {"available": True, "data": None}
            data = get_full_company_data(name)
            return {"available": True, "data": data}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def enrich_with_people(self, question: str) -> Dict[str, Any]:
        """Fetch person profile via Proxycurl (LinkedIn) if available."""
        if not self._enrichment_available:
            return {"available": False, "reason": "enrichment deps missing"}
        try:
            from core.external_enrichment import get_linkedin_profile_proxycurl
            name = self._extract_candidate_name_or_company(question)
            if not name:
                return {"available": True, "data": None}
            data = get_linkedin_profile_proxycurl(name)
            return {"available": True, "data": data}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def enrich_with_web(self, question: str) -> Dict[str, Any]:
        """Web research via Perplexity if available."""
        if not self._enrichment_available:
            return {"available": False, "reason": "enrichment deps missing"}
        try:
            from core.perplexity_utils import search_perplexity
            res = search_perplexity(question, return_url=True)
            return {"available": True, "data": res}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def analyze_question_enriched(self, question: str) -> Dict[str, Any]:
        """Task-aware flow with NO vector DB usage.
        - Market/segment deep dive: try local report snippets; if none found, use web search
        - Company: web search + CoreSignal (additional)
        - People: LinkedIn (Proxycurl) then general web fallback
        - Fund: CoreSignal then web fallback
        """
        task = self.classify_task(question)
        enrichment: Dict[str, Any] = {"task": task}
        sources: List[Dict[str, Any]] = []
        validation: Dict[str, Any] = {}
        answer: str = ""

        # 1) Market deep dive → cached market data first, then web
        if task == "market_deep_dive":
            cached_snippets = self._load_market_cache(include_tables=True)
            filtered = self._filter_and_score_cache(cached_snippets, question, min_sector_match=True, limit=30)
            if not filtered and not cached_snippets:
                # If no cache, do nothing here (web fallback below). No live extraction per user request.
                pass
            if filtered:
                # Convert to snippet format expected by _llm_answer_with_snippets
                norm = [{"text": it.get("text", ""), "source": it.get("source", "unknown"), "page": it.get("page", 1)} for it in filtered]
                answer = self._llm_answer_with_snippets(question, norm)
                for s in norm:
                    sources.append({"source": s["source"], "page": s["page"], "temporal_valid": True})
            if not sources and not answer:
                web = self.enrich_with_web(question)
                enrichment["web"] = web
                answer = (web.get("data") or {}).get("answer", "No data found.")
                url = (web.get("data") or {}).get("url")
                if url:
                    sources.append({"source": url, "temporal_valid": True})

        # 2) Company → web + CoreSignal (synthesize with LLM)
        elif task == "company":
            # Derive LinkedIn/company site via Perplexity first to improve CoreSignal match
            name_hint = self._extract_candidate_name_or_company(question)
            hints = self._perplexity_get_company_hints(name_hint or question)
            web_li_url = hints.get("linkedin_url")
            website_domain = hints.get("website_domain", "")

            # General web content for synthesis
            web = self.enrich_with_web(question)
            enrichment["web"] = web
            web_ans = (web.get("data") or {}).get("answer", "")
            web_url = (web.get("data") or {}).get("url")
            if web_url:
                sources.append({"source": web_url, "temporal_valid": True})
            if web_li_url:
                sources.append({"source": web_li_url, "temporal_valid": True})

            # Try CoreSignal with website hint if available
            try:
                from core.coresignal_utils import get_full_company_data as _cs_get
                # Prefer website-only search if we have domain; skip name search per request
                if website_domain:
                    cs_payload = _cs_get(name_hint or question, website=website_domain)
                else:
                    cs_payload = _cs_get(name_hint or question)
                cs = {"available": True, "data": cs_payload}
            except Exception as e:
                cs = {"available": False, "error": str(e)}
            enrichment["coresignal"] = cs
            cs_payload = cs.get("data")
            if cs_payload:
                sources.append({"source": "CoreSignal", "temporal_valid": True})

            contexts = []
            if web_ans:
                contexts.append({"label": f"Web ({web_url})" if web_url else "Web", "content": web_ans})
            if cs_payload:
                try:
                    import json as _json
                    cs_text = _json.dumps(cs_payload, indent=2)[:4000]
                except Exception:
                    cs_text = str(cs_payload)[:4000]
                contexts.append({"label": "CoreSignal", "content": cs_text})
            if contexts:
                answer = self._llm_answer_with_external_contexts(question, contexts)
            else:
                answer = web_ans or "No data found."

        # 3) People → Perplexity web search (LinkedIn first), then synthesize with LLM
        elif task == "person":
            contexts: List[Dict[str, str]] = []
            # 1) LinkedIn-focused query
            web = self.enrich_with_web(f"site:linkedin.com {question}")
            enrichment["web_linkedin"] = web
            web_ans = (web.get("data") or {}).get("answer", "")
            web_url = (web.get("data") or {}).get("url")
            if web_url:
                sources.append({"source": web_url, "temporal_valid": True})
            if web_ans:
                contexts.append({"label": f"Web ({web_url})" if web_url else "Web", "content": web_ans})

            # 2) Bio/university/profile query (second pass) regardless, to match old richness
            bio_query = f"{question} biography university profile publications honors awards"
            web_bio = self.enrich_with_web(bio_query)
            enrichment["web_bio"] = web_bio
            web_bio_ans = (web_bio.get("data") or {}).get("answer", "")
            web_bio_url = (web_bio.get("data") or {}).get("url")
            if web_bio_url:
                sources.append({"source": web_bio_url, "temporal_valid": True})
            if web_bio_ans:
                contexts.append({"label": f"Web ({web_bio_url})" if web_bio_url else "Web", "content": web_bio_ans})

            # 3) General web fallback if still thin
            if not contexts:
                web2 = self.enrich_with_web(question)
                enrichment["web_fallback"] = web2
                web2_ans = (web2.get("data") or {}).get("answer", "")
                web2_url = (web2.get("data") or {}).get("url")
                if web2_url:
                    sources.append({"source": web2_url, "temporal_valid": True})
                if web2_ans:
                    contexts.append({"label": f"Web ({web2_url})" if web2_url else "Web", "content": web2_ans})

            # Specialized synthesis for bios
            answer = self._llm_answer_with_external_contexts_for_bio(question, contexts) if contexts else "No data found."

        # 4) Fund → web then CoreSignal; synthesize with LLM
        elif task == "fund":
            name_hint = self._extract_candidate_name_or_company(question)
            hints = self._perplexity_get_company_hints(name_hint or question)
            web_li_url = hints.get("linkedin_url")
            website_domain = hints.get("website_domain", "")

            web = self.enrich_with_web(question)
            enrichment["web"] = web
            web_ans = (web.get("data") or {}).get("answer", "")
            web_url = (web.get("data") or {}).get("url")
            if web_url:
                sources.append({"source": web_url, "temporal_valid": True})
            if web_li_url:
                sources.append({"source": web_li_url, "temporal_valid": True})

            # Try CoreSignal with website hint if available
            try:
                from core.coresignal_utils import get_full_company_data as _cs_get
                if website_domain:
                    cs_payload = _cs_get(name_hint or question, website=website_domain)
                else:
                    cs_payload = _cs_get(name_hint or question)
                cs = {"available": True, "data": cs_payload}
            except Exception as e:
                cs = {"available": False, "error": str(e)}
            enrichment["coresignal"] = cs
            cs_payload = cs.get("data")
            if cs_payload:
                sources.append({"source": "CoreSignal", "temporal_valid": True})

            contexts = []
            if web_ans:
                contexts.append({"label": f"Web ({web_url})" if web_url else "Web", "content": web_ans})
            if cs_payload:
                try:
                    import json as _json
                    cs_text = _json.dumps(cs_payload, indent=2)[:4000]
                except Exception:
                    cs_text = str(cs_payload)[:4000]
                contexts.append({"label": "CoreSignal", "content": cs_text})
            if contexts:
                answer = self._llm_answer_with_external_contexts(question, contexts)
            else:
                answer = web_ans or "No data found."

        # Generic → simple LLM answer (no enrichment)
        else:
            base = self.analyze_question(question)
            answer = base.get("answer", "")
            sources.extend(base.get("sources", []))
            validation = base.get("validation", {})

        return {
            "answer": answer,
            "sources": sources,
            "validation": validation,
            "classification": task,
            "enrichment": enrichment,
        }

    def _gather_report_pdfs(self) -> List[Path]:
        """Collect candidate PDF report paths for snippet extraction (no vector DB)."""
        candidates: List[Path] = []
        roots = [Path("web_scraping/data/vc_reports/test_sample"), Path("web_scraping/data/vc_reports"), Path("data/vc_reports")]
        seen: Set[str] = set()
        for root in roots:
            if not root.exists():
                continue
            for p in root.rglob("*.pdf"):
                key = str(p.resolve())
                if key not in seen:
                    seen.add(key)
                    candidates.append(p)
        return candidates

    def _extract_snippets_from_reports(self, question: str, max_snippets: int = 8) -> List[Dict[str, Any]]:
        """Lightweight, RAG-less snippet extraction using simple keyword filtering."""
        keywords = list(self._extract_keywords(question))
        if not keywords:
            return []
        snippets: List[Dict[str, Any]] = []
        for pdf_path in self._gather_report_pdfs():
            try:
                with fitz.open(str(pdf_path)) as doc:
                    for idx in range(doc.page_count):
                        page = doc.load_page(idx)
                        text = (page.get_text("text") or "").strip()
                        if not text:
                            continue
                        lower = text.lower()
                        if any(kw in lower for kw in keywords):
                            pos_list = [lower.find(kw) for kw in keywords if kw in lower]
                            pos = min(pos_list) if pos_list else 0
                            start = max(0, pos - 400)
                            end = min(len(text), pos + 400)
                            snippets.append({"text": text[start:end], "source": pdf_path.name, "page": idx + 1})
                            if len(snippets) >= max_snippets:
                                return snippets
            except Exception:
                try:
                    with pdfplumber.open(str(pdf_path)) as pdf:
                        for idx, pg in enumerate(pdf.pages, start=1):
                            text = (pg.extract_text() or "").strip()
                            if not text:
                                continue
                            lower = text.lower()
                            if any(kw in lower for kw in keywords):
                                pos_list = [lower.find(kw) for kw in keywords if kw in lower]
                                pos = min(pos_list) if pos_list else 0
                                start = max(0, pos - 400)
                                end = min(len(text), pos + 400)
                                snippets.append({"text": text[start:end], "source": pdf_path.name, "page": idx})
                                if len(snippets) >= max_snippets:
                                    return snippets
                except Exception:
                    continue
        return snippets

    def _llm_answer_with_snippets(self, question: str, snippets: List[Dict[str, Any]]) -> str:
        context = "\n\n---\n\n".join([f"[Source: {s['source']}, Page {s['page']}]\n{s['text']}" for s in snippets])
        prompt = (
            "You are a VC research assistant. Use ONLY the following snippets from local reports to answer the question.\n"
            "If the snippets don't contain enough information, say that explicitly.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )
        resp = self.llm.invoke(prompt)
        return getattr(resp, "content", str(resp))

    def _llm_answer_with_external_contexts(self, question: str, contexts: List[Dict[str, str]]) -> str:
        blocks = []
        for c in contexts:
            label = c.get("label", "Source")
            content = c.get("content", "")
            blocks.append(f"[{label}]\n{content}")
        context = "\n\n---\n\n".join(blocks)
        prompt = (
            "You are a VC research assistant. Synthesize the following sources to answer the question.\n"
            "Cite sources inline as (source: CoreSignal) or (source: <url>) where appropriate.\n"
            "If information is missing, state that explicitly.\n\n"
            f"Sources:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )
        resp = self.llm.invoke(prompt)
        return getattr(resp, "content", str(resp))

    def _llm_answer_with_external_contexts_for_bio(self, question: str, contexts: List[Dict[str, str]]) -> str:
        blocks = []
        for c in contexts:
            label = c.get("label", "Source")
            content = c.get("content", "")
            blocks.append(f"[{label}]\n{content}")
        context = "\n\n---\n\n".join(blocks)
        prompt = (
            "You are a research assistant creating a concise professional bio.\n"
            "Use the sources to extract: current role and affiliation, past roles, education, research interests, notable publications, awards, and links.\n"
            "Output a short paragraph followed by bullets. Always cite sources inline as (source: <url>). If uncertain, say so.\n\n"
            f"Sources:\n{context}\n\nPerson query: {question}\n\nAnswer:"
        )
        resp = self.llm.invoke(prompt)
        return getattr(resp, "content", str(resp))

    # --- Cached market data helpers ---
    def _load_market_cache(self, include_tables: bool = False) -> List[Dict[str, Any]]:
        """Load flattened items from cached_market_data.
        When include_tables=True, also include flattened table rows.
        Each item: {text, source, page}.
        """
        base_dir = Path("web_scraping/data/vc_reports/cached_market_data")
        index_path = base_dir / "index.json"
        items: List[Dict[str, Any]] = []
        try:
            if not index_path.exists():
                return []
            with open(index_path, "r") as f:
                index = json.load(f)
            for fmeta in index.get("files", []):
                try:
                    jf = base_dir / fmeta.get("json", "")
                    if not jf.exists():
                        continue
                    with open(jf, "r") as jfh:
                        payload = json.load(jfh)
                    source = payload.get("file", fmeta.get("file", "unknown"))
                    for p in (payload.get("pages") or []):
                        text = (p.get("text") or "").strip()
                        if not text:
                            continue
                        items.append({"text": text, "source": source, "page": p.get("page", 1)})
                    if include_tables:
                        for t in (payload.get("tables") or []):
                            rows = t.get("rows") or []
                            if not rows:
                                continue
                            # join cells into lines
                            lines = [", ".join([(c or "").strip() for c in row]) for row in rows]
                            t_text = "\n".join(lines).strip()
                            if t_text:
                                items.append({
                                    "text": f"Table (p{t.get('page')} t{t.get('table_index')}):\n{t_text}",
                                    "source": source,
                                    "page": t.get("page", 1),
                                })
                except Exception:
                    continue
        except Exception:
            return []
        return items

    def _filter_and_score_cache(self, cache: List[Dict[str, Any]], question: str, min_sector_match: bool = True, limit: int = 30) -> List[Dict[str, Any]]:
        # Expand keyword variants
        q = question.lower()
        synonyms = {
            "pre-money": ["premoney", "pre money"],
            "deal value": ["deal size", "transaction value"],
            "development": ["dev"],
        }
        base_keywords = list(self._extract_keywords(question))
        expanded: Set[str] = set(base_keywords)
        for k, alts in synonyms.items():
            if k in q:
                expanded.update(alts)
        # sector token heuristic
        sector_tokens = [t for t in ["gaming", "insurtech", "biotech", "bio tools", "biotools", "quantum", "e-commerce", "ecommerce", "foodtech", "pharma"] if t in q]
        def score_item(text: str, source: str) -> int:
            s = 0
            low = text.lower()
            for kw in expanded:
                if kw in low:
                    s += 1
            # bonus for sector tokens
            for st in sector_tokens:
                if st in low:
                    s += 3
                if st.replace(" ", "") in low:
                    s += 2
                if st in source.lower():
                    s += 4
            return s
        # Filter (optional sector requirement) and score
        scored: List[tuple[int, Dict[str, Any]]] = []
        for item in cache:
            text = item.get("text", "")
            low = text.lower()
            if min_sector_match and sector_tokens:
                if not any(st in low or st.replace(" ", "") in low or st in item.get("source", "").lower() for st in sector_tokens):
                    continue
            s = score_item(text, item.get("source", ""))
            if s > 0:
                scored.append((s, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:limit]]

    def _validate_temporal_context(self, question: str, context: List[Any]) -> bool:
        """Validate that the temporal context of the question matches the data."""
        # Extract year from question if present
        year_match = re.search(r'20\d{2}', question)
        if not year_match:
            return True
        
        target_year = year_match.group(0)
        
        # Check if any context documents contain data from different years
        for doc in context:
            if str(target_year) not in doc.page_content:
                return False
        return True

    def get_insurtech_deal_activity(self) -> Dict:
        """Get current deal activity size for Insurtech in the most recent quarter."""
        return self.analyze_question("What's the current deal activity size for Insurtech in the most recent financial quarter?")

    def get_biotech_exits(self) -> Dict:
        """Get total value of exits in the biotechnology/bio tools space in Q1 2025."""
        return self.analyze_question("What's the total value of exits in the biotechnology/bio tools space in Q1 2025?")

    def get_top_spinout_institutions(self) -> Dict:
        """Get top 3 academic institutions by spin out activity in the UK."""
        return self.analyze_question("What are the top 3 academic institutions by spin out activity in the UK? How many companies do they spin out on average individually?")

    def get_top_spinout_sector(self) -> Dict:
        """Get top sector of UK academic spinouts."""
        return self.analyze_question("What is the top sector of UK academic spinouts?")

    def get_top_quantum_subsector(self) -> Dict:
        """Get top sub-sector of Quantum Computing by number of companies."""
        return self.analyze_question("What's the top sub-sector of Quantum Computing by number of companies generated?")

    def get_gaming_cagr(self) -> Dict:
        """Get CAGR of median gaming early-stage VC deal value and pre-money valuation."""
        return self.analyze_question("What's the CAGR of median gaming early-stage VC deal value and pre-money valuation ($M) in the segment of development?")

    def _clean_metadata(self, metadata: dict) -> dict:
        """Clean and filter document metadata to ensure compatibility with Chroma."""
        # Keep only essential metadata
        essential_metadata = {
            "source": str(metadata.get("source", "Unknown")),
            "page": str(metadata.get("page_number", 1)),
            "has_visual": bool("figure" in str(metadata.get("category", "")).lower())
        }
        
        # Filter out any remaining complex metadata
        return filter_complex_metadata(essential_metadata)

    def _process_pdf_content(self, content: str, metadata: dict) -> Document:
        """Process PDF content and create a Document object."""
        # Clean and normalize the text
        cleaned_content = ' '.join(content.split())
        
        # Only create document if content is meaningful
        if len(cleaned_content.strip()) > 50:
            return Document(
                page_content=cleaned_content,
                metadata=self._clean_metadata(metadata)
            )
        return None

    def _initialize_vector_store(self, report_path: str) -> int:
        """Initialize the vector store with all PDFs found under report_path.

        Returns the number of document chunks indexed.
        """
        documents: list[Document] = []
        min_chars = 5
        report_root = Path(report_path)
        pdf_files = [p for p in report_root.rglob('*') if p.is_file() and p.suffix.lower() == '.pdf']
        if not pdf_files:
            logger.info(f"No PDFs found under {report_root.resolve()}")
        for pdf_file in pdf_files:
            try:
                collected_for_file = 0
                # 1) Try PyMuPDF per page
                try:
                    with fitz.open(str(pdf_file)) as doc:
                        for page_index in range(doc.page_count):
                            page = doc.load_page(page_index)
                            text = page.get_text("text") or ""
                            text = ' '.join(text.split())
                            if len(text) >= min_chars:
                                documents.append(
                                    Document(
                                        page_content=text,
                                        metadata=self._clean_metadata({
                                            "source": pdf_file.name,
                                            "page_number": page_index + 1,
                                            "category": "text",
                                        }),
                                    )
                                )
                                collected_for_file += 1
                except Exception as fe:
                    logger.debug(f"PyMuPDF failed for {pdf_file.name}: {fe}")

                # 2) If nothing collected, try pdfminer full text
                if collected_for_file == 0:
                    try:
                        text = pdfminer_extract_text(str(pdf_file)) or ""
                        text = ' '.join(text.split())
                        if len(text) >= min_chars:
                            documents.append(
                                Document(
                                    page_content=text,
                                    metadata=self._clean_metadata({
                                        "source": pdf_file.name,
                                        "page_number": 1,
                                        "category": "text",
                                    }),
                                )
                            )
                            collected_for_file += 1
                    except Exception as me:
                        logger.debug(f"pdfminer failed for {pdf_file.name}: {me}")

                # 3) If still nothing, try pdfplumber per page
                if collected_for_file == 0:
                    try:
                        with pdfplumber.open(str(pdf_file)) as pdf:
                            for page_index, page in enumerate(pdf.pages, start=1):
                                try:
                                    text = page.extract_text() or ""
                                    text = ' '.join(text.split())
                                    if len(text) >= min_chars:
                                        documents.append(
                                            Document(
                                                page_content=text,
                                                metadata=self._clean_metadata({
                                                    "source": pdf_file.name,
                                                    "page_number": page_index,
                                                    "category": "text",
                                                }),
                                            )
                                        )
                                        collected_for_file += 1
                                    # Also extract tables as textual chunks
                                    try:
                                        tables = page.extract_tables() or []
                                        for t_idx, table in enumerate(tables, 1):
                                            try:
                                                rows = [
                                                    ", ".join([(cell or "").strip() for cell in row])
                                                    for row in table
                                                ]
                                                table_str = "\n".join(rows)
                                                table_str = ' '.join(table_str.split())
                                                if len(table_str) >= min_chars:
                                                    documents.append(
                                                        Document(
                                                            page_content=f"Table (p{page_index} t{t_idx}): {table_str}",
                                                            metadata=self._clean_metadata({
                                                                "source": pdf_file.name,
                                                                "page_number": page_index,
                                                                "category": "table",
                                                            }),
                                                        )
                                                    )
                                                    collected_for_file += 1
                                            except Exception:
                                                continue
                                    except Exception:
                                        pass
                                except Exception as pe:
                                    logger.debug(f"Skipping page {page_index} of {pdf_file.name}: {pe}")
                    except Exception as pe2:
                        logger.debug(f"pdfplumber failed for {pdf_file.name}: {pe2}")

                # 4) As a last resort, OCR pages
                if collected_for_file == 0:
                    try:
                        images = convert_from_path(str(pdf_file), dpi=200)
                        ocr_text_accumulator: list[str] = []
                        for img in images:
                            try:
                                t = pytesseract.image_to_string(img) or ""
                                t = ' '.join(t.split())
                                if len(t) >= min_chars:
                                    ocr_text_accumulator.append(t)
                            except Exception as oe:
                                logger.debug(f"OCR failed for a page in {pdf_file.name}: {oe}")
                        if ocr_text_accumulator:
                            combined_text = "\n".join(ocr_text_accumulator)
                            documents.append(
                                Document(
                                    page_content=combined_text,
                                    metadata=self._clean_metadata({
                                        "source": pdf_file.name,
                                        "page_number": 1,
                                        "category": "ocr_text",
                                    }),
                                )
                            )
                            collected_for_file += 1
                    except Exception as oe2:
                        logger.debug(f"OCR fallback failed for {pdf_file.name}: {oe2}")

                logger.info(f"Processed {pdf_file.name}. Pages/docs collected: {collected_for_file}")
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                continue

        if not documents:
            logger.warning("No valid documents found to index.")
            return 0

        # Chunk documents
        chunker = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", ".", " "]
        )
        chunked_documents: list[Document] = []
        for d in documents:
            try:
                for c in chunker.split_text(d.page_content):
                    if c and len(c.strip()) > 0:
                        chunked_documents.append(Document(page_content=c, metadata=d.metadata))
            except Exception as ce:
                logger.debug(f"Chunking failed for a document from {d.metadata.get('source','unknown')}: {ce}")

        if not chunked_documents:
            chunked_documents = documents

        self.vector_store = Chroma.from_documents(
            documents=chunked_documents,
            embedding=self.embeddings,
            collection_name="vc_reports",
            persist_directory="./chroma_db",
        )
        logger.info(
            f"Vector store initialized with {len(chunked_documents)} chunks (from {len(documents)} source docs)"
        )
        return len(chunked_documents)

    def _create_qa_chain(self):
        """Create the question-answering chain."""
        # Create a prompt template for the QA chain
        prompt = ChatPromptTemplate.from_template(
            """You are a helpful AI assistant analyzing venture capital reports. 
            Use the following pieces of context to answer the question at the end.
            If you don't know the answer, explain why you can't find the specific information in the context.
            If the question is about temporal data (dates, quarters, years), make sure to validate the time period mentioned in the context.
            If the question is about specific companies or sectors, make sure to validate the data against the context.
            If the question is about percentages or calculations, make sure to validate the numbers against the context.

            Context: {context}

            Question: {question}

            Guidelines:
            1. If you can't find the exact information, explain what information is available
            2. If the data is from a different time period, mention this
            3. If the context is unclear or incomplete, explain what's missing
            4. Always cite your sources when possible

            Answer:"""
        )

        # Create a simple QA chain with better context handling
        def format_docs(docs):
            """Format documents with clear separation and source attribution."""
            formatted = []
            for doc in docs:
                source = doc.metadata.get("source", "Unknown")
                page = doc.metadata.get("page", "Unknown")
                formatted.append(f"[Source: {source}, Page {page}]\n{doc.page_content}\n")
            return "\n---\n".join(formatted)

        self.qa_chain = (
            {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def _validate_temporal_data(self, question: str, docs: List[Any]) -> Dict[str, Any]:
        """Validate temporal data in the question against the context."""
        try:
            # Extract year from question if present
            year_match = re.search(r'20\d{2}', question)
            if not year_match:
                return {"valid": True, "reason": "No specific year mentioned"}
            
            target_year = year_match.group(0)
            
            # Check if any context documents contain data from different years
            for doc in docs:
                if str(target_year) not in doc.page_content:
                    return {
                        "valid": False,
                        "reason": f"Data from {target_year} not found in context"
                    }
            return {"valid": True, "reason": f"Data from {target_year} validated"}
        except Exception as e:
            return {"valid": False, "reason": f"Error in temporal validation: {str(e)}"}

    def _validate_company_data(self, question: str, docs: List[Any]) -> Dict[str, Any]:
        """Validate company/sector data in the question against the context."""
        try:
            # Simple validation - check if any company/sector terms are found
            company_terms = ["company", "sector", "industry", "startup", "venture"]
            found_terms = [term for term in company_terms if term.lower() in question.lower()]
            
            if not found_terms:
                return {"valid": True, "reason": "No company/sector specific question"}
            
            # Check if terms appear in context
            for doc in docs:
                if any(term.lower() in doc.page_content.lower() for term in found_terms):
                    return {"valid": True, "reason": "Company/sector data found in context"}
            
            return {"valid": False, "reason": "Company/sector data not found in context"}
        except Exception as e:
            return {"valid": False, "reason": f"Error in company validation: {str(e)}"}

    def _validate_numerical_data(self, question: str, docs: List[Any]) -> Dict[str, Any]:
        """Validate numerical data in the question against the context."""
        try:
            # Check for numerical terms
            numerical_terms = ["percentage", "number", "amount", "value", "total", "average"]
            found_terms = [term for term in numerical_terms if term.lower() in question.lower()]
            
            if not found_terms:
                return {"valid": True, "reason": "No numerical data requested"}
            
            # Check if numerical data appears in context
            for doc in docs:
                if any(term.lower() in doc.page_content.lower() for term in found_terms):
                    return {"valid": True, "reason": "Numerical data found in context"}
            
            return {"valid": False, "reason": "Numerical data not found in context"}
        except Exception as e:
            return {"valid": False, "reason": f"Error in numerical validation: {str(e)}"}

    def get_uk_spinout_analysis(self) -> Dict:
        """Get analysis of UK academic spinout activity."""
        return self.analyze_question(
            "What are the top 3 academic institutions by spin out activity in the UK, "
            "how many companies do they spin out on average individually, "
            "and what is the top sector of UK academic spinouts?"
        )

    def get_quantum_computing_analysis(self) -> Dict:
        """Get analysis of Quantum Computing sub-sectors."""
        return self.analyze_question(
            "What's the top sub-sector of Quantum Computing by number of companies generated? "
            "Please provide specific numbers and trends."
        )

    def get_gaming_deal_analysis(self) -> Dict:
        """Get analysis of gaming early-stage VC deal values."""
        return self.analyze_question(
            "What's the CAGR of median gaming early-stage VC deal value and pre-money valuation ($M) "
            "in the segment of development? Please provide specific numbers and trends."
        ) 