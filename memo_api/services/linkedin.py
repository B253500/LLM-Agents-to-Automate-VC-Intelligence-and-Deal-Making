import os
import asyncio
import aiohttp

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
