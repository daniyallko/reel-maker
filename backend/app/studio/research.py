import asyncio
import os
from urllib.parse import urlparse

import httpx
from ddgs import DDGS

from app.studio.schemas import SourceCitation


class FirecrawlResearch:
    def __init__(self, post=None):
        self.api_key = os.environ.get("FIRECRAWL_API_KEY")
        self.post = post

    async def research(self, url: str, title: str) -> list[SourceCitation]:
        if not self.api_key:
            return []
        if self.post is None:
            client = httpx.AsyncClient(timeout=12)
            post = client.post
        else:
            post = self.post
        response = await post(
            "https://api.firecrawl.dev/v1/search",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "query": title,
                "limit": 3,
                "timeout": 10000,
                "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
            },
        )
        response.raise_for_status()
        payload = response.json()
        citations = []
        for item in payload.get("data", [])[:3]:
            claim = item.get("description") or item.get("markdown", "")[:500]
            citations.append(SourceCitation(
                url=item.get("url", url),
                title=item.get("title", title),
                claim=claim or "Source discovered through Firecrawl",
            ))
        return citations


async def research_url(url: str, title: str, timeout: float = 10) -> list[SourceCitation]:
    hostname = urlparse(url).hostname or title
    query_title = title if not title.startswith("http") else hostname

    async def firecrawl() -> list[SourceCitation]:
        provider = FirecrawlResearch()
        return await provider.research(url, query_title)

    async def query(search: str) -> list[SourceCitation]:
        def run() -> list[SourceCitation]:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(search, max_results=2))
                return [
                    SourceCitation(
                        url=item.get("href", url),
                        title=item.get("title", search),
                        claim=item.get("body", "Source discovered during research"),
                    )
                    for item in results
                ]
            except Exception:
                return []
        return await asyncio.to_thread(run)

    try:
        if os.environ.get("FIRECRAWL_API_KEY"):
            citations = await asyncio.wait_for(firecrawl(), timeout=timeout)
            if citations:
                return citations
    except Exception:
        pass

    try:
        batches = await asyncio.wait_for(asyncio.gather(
            query(f"{query_title} product launch reviews"),
            query(f"{query_title} founder story"),
        ), timeout=timeout)
        citations = [citation for batch in batches for citation in batch]
    except Exception:
        citations = []
    if not citations:
        citations.append(SourceCitation(url=url, title=title, claim="Primary source supplied by the user"))
    return citations
