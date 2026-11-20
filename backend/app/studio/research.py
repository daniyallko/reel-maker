import asyncio
import os
from urllib.parse import urlparse, urlsplit, urlunsplit

import httpx
from ddgs import DDGS

from app.studio.schemas import EvidenceClaim, ResearchPlan, ResearchReport, SourceBundle, SourceCitation

MAX_RESEARCH_SOURCES = 8
MAX_SOURCE_CONTENT = 4_000
MAX_TOTAL_CONTENT = 24_000


def search_ddgs(query: str, max_results: int = 2) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


def _normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    if parts.scheme and parts.netloc and not path:
        path = "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _bounded_sources(citations: list[SourceCitation]) -> list[SourceCitation]:
    bounded = []
    seen = set()
    remaining = MAX_TOTAL_CONTENT
    for citation in citations:
        normalized = _normalized_url(citation.url)
        if normalized in seen:
            continue
        seen.add(normalized)
        content = citation.content[:min(MAX_SOURCE_CONTENT, remaining)]
        remaining -= len(content)
        bounded.append(citation.model_copy(update={"content": content}))
        if len(bounded) == MAX_RESEARCH_SOURCES:
            break
    return bounded


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
                content=item.get("markdown") or item.get("description") or "",
            ))
        return citations


async def _ddgs_citations(url: str, search: str) -> list[SourceCitation]:
    def run() -> list[SourceCitation]:
        try:
            results = search_ddgs(search)
        except Exception:
            return []
        citations = []
        for item in results:
            body = item.get("body") or ""
            citations.append(SourceCitation(
                url=item.get("href", url),
                title=item.get("title", search),
                claim=body or "Source discovered during research",
                content=body,
            ))
        return citations

    return await asyncio.to_thread(run)


async def research_queries(url: str, queries: list[str], timeout: float = 10) -> list[SourceCitation]:
    try:
        if os.environ.get("FIRECRAWL_API_KEY"):
            provider = FirecrawlResearch()
            batches = await asyncio.wait_for(asyncio.gather(*(
                provider.research(url, query) for query in queries
            )), timeout=timeout)
            citations = _bounded_sources([citation for batch in batches for citation in batch])
            if citations:
                return citations
    except Exception:
        pass

    try:
        batches = await asyncio.wait_for(asyncio.gather(*(
            _ddgs_citations(url, query) for query in queries
        )), timeout=timeout)
        citations = _bounded_sources([citation for batch in batches for citation in batch])
    except Exception:
        citations = []
    if citations or url.startswith("inline://"):
        return citations
    return [SourceCitation(url=url, title=url, claim="Primary source supplied by the user")]


def fallback_research_plan(bundle: SourceBundle, style: str) -> ResearchPlan:
    topic = " ".join((bundle.title or bundle.dom_copy or bundle.source_url).split())
    return ResearchPlan(
        topic=topic,
        angle=style.replace("_", " ") or "evidence and context",
        queries=[
            topic,
            f"{topic} evidence and context",
            f"{topic} challenges and impact",
        ],
    )


def fallback_research_report(
    bundle: SourceBundle,
    plan: ResearchPlan,
    sources: list[SourceCitation],
) -> ResearchReport:
    citations = _bounded_sources([*bundle.citations, *sources])
    if not citations and bundle.dom_copy.strip():
        citations = [SourceCitation(
            url=bundle.source_url,
            title=plan.topic,
            claim=bundle.dom_copy.strip()[:500],
            content=bundle.dom_copy,
        )]
        citations = _bounded_sources(citations)
    claims = []
    for index, citation in enumerate(citations):
        text = (citation.claim or citation.content[:500]).strip()
        if text:
            claims.append(EvidenceClaim(text=text, source_refs=[index]))
    return ResearchReport(
        topic=plan.topic,
        angle=plan.angle,
        summary=" ".join(claim.text for claim in claims),
        claims=claims,
        sources=citations,
        queries=plan.queries,
        external_research=any(not source.url.startswith("inline://") for source in sources),
        provider="deterministic",
    )


async def research_url(url: str, title: str, timeout: float = 10) -> list[SourceCitation]:
    hostname = urlparse(url).hostname or title
    query_title = title if not title.startswith("http") else hostname
    sources = await research_queries(url, [
        f"{query_title} product launch reviews",
        f"{query_title} founder story",
    ], timeout=timeout)
    if len(sources) == 1 and sources[0].url == url and sources[0].claim == "Primary source supplied by the user":
        return [sources[0].model_copy(update={"title": title})]
    return sources
