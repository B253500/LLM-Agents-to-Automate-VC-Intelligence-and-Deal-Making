from googlesearch import search
import requests
from bs4 import BeautifulSoup


def google_search(query, num_results=3):
    try:
        return list(search(query, num_results=num_results, lang="en"))
    except Exception as e:
        print(f"Google search failed: {e}")
        return []


def fetch_page_text(url, max_chars=1500):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, timeout=5, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script/style
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator="\n")
        return text[:max_chars]
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""


def get_hybrid_context(profile, topic, k_local=3, k_web=2):
    # Local context
    from core.vector_store import query_doc

    name = getattr(profile, "name", "") or ""
    ceo = getattr(profile, "founder_name", "") or getattr(profile, "ceo", "") or ""
    local = query_doc(getattr(profile, "startup_id", None), topic, k=k_local)
    # Google web context
    search_query = f"{name} {topic}"
    urls = google_search(search_query, num_results=k_web)
    web_texts = [fetch_page_text(url) for url in urls if url]
    # Combine, truncate if too long
    context = "\n\n".join(local + web_texts)[:4000]
    return context or "No local or web info found."
