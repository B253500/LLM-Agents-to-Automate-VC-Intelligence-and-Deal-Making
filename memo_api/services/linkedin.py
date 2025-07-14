import os, requests, asyncio, aiohttp

BASE = "https://nubela.co/proxycurl/api/v2/linkedin"
HEAD = {"Authorization": f"Bearer {os.getenv('PROXYCURL_API_KEY', '')}"}


async def fetch(session, url):
    if not url:
        return {}
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"https://www.linkedin.com/in/{url}"
    async with session.get(
        BASE, params={"url": url, "use_cache": "if-present"}, headers=HEAD
    ) as r:
        return await r.json()


async def batch_fetch(urls, trace_id):
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*(fetch(session, u) for u in urls))


def enrich_executives_from_linkedin(company_name):
    """
    Given a company name, fetches a list of executives (name, role, linkedin) from Proxycurl's LinkedIn Company Employees endpoint.
    Returns a list of dicts: { 'name': ..., 'role': ..., 'linkedin': ... }
    """
    import requests
    api_key = os.getenv("PROXYCURL_API_KEY", "")
    if not api_key or not company_name:
        return []
    # Proxycurl Company Employees endpoint
    url = "https://nubela.co/proxycurl/api/linkedin/company/employees"
    params = {
        "company_name": company_name,
        "role": "executive",
        "enrich_profiles": "enrich"
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code != 200:
            return []
        data = resp.json()
        # Expecting a list of employees with fields: name, title, linkedin_profile_url
        execs = []
        for emp in data.get("employees", []):
            execs.append({
                "name": emp.get("name", "Unknown"),
                "role": emp.get("title", "Unknown"),
                "linkedin": emp.get("linkedin_profile_url", "")
            })
        return execs
    except Exception as e:
        print(f"[LinkedIn Enrichment] Error: {e}")
        return []
