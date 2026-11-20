from pathlib import Path

import pytest
from pydantic import ValidationError

from app.studio.research import fallback_research_plan, fallback_research_report, research_queries, research_url
from app.studio.schemas import EvidenceClaim, ResearchPlan, ResearchReport, SourceBundle, SourceCitation
from app.studio.sources import ingest_text


def test_text_topic_builds_external_research_plan():
    plan = fallback_research_plan(ingest_text("Ocean cleanup robots"), "deep_dive")
    assert plan.topic == "Ocean cleanup robots"
    assert 1 <= len(plan.queries) <= 4
    assert all("Ocean cleanup robots" in query for query in plan.queries)


def test_research_plan_requires_one_to_four_queries():
    with pytest.raises(ValidationError):
        ResearchPlan(topic="Ocean cleanup robots", angle="deep dive", queries=[])
    with pytest.raises(ValidationError):
        ResearchPlan(topic="Ocean cleanup robots", angle="deep dive", queries=["one", "two", "three", "four", "five"])


def test_image_only_research_retains_supplied_evidence():
    bundle = ingest_text("Uploaded image: robot.png", title="robot.png")
    plan = fallback_research_plan(bundle, "deep_dive")
    report = fallback_research_report(bundle, plan, [])
    assert report.provider == "deterministic"
    assert report.claims
    assert report.sources[0].url.startswith("inline://")


def test_research_report_rejects_invalid_claim_references():
    source = SourceCitation(url="inline://text", title="Robot notes", claim="Robots collect plastic")
    with pytest.raises(ValidationError):
        ResearchReport(
            topic="Robots",
            angle="deep dive",
            summary="Robots collect plastic",
            claims=[EvidenceClaim(text="Robots collect plastic", source_refs=[1])],
            sources=[source],
            queries=["robots"],
            external_research=False,
            provider="deterministic",
        )


@pytest.mark.asyncio
async def test_topic_research_dedupes_and_bounds_sources(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr("app.studio.research.search_ddgs", lambda query, max_results=2: [
        {"href": "https://example.com/robots", "title": "Robots", "body": "Ocean cleanup evidence"}
    ])
    sources = await research_queries("inline://text", ["ocean robots", "ocean robots explained"], timeout=1)
    assert len(sources) == 1
    assert sources[0].content == "Ocean cleanup evidence"
    assert "content" not in sources[0].model_dump()


@pytest.mark.asyncio
async def test_topic_research_bounds_source_count_and_retrieved_content(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr("app.studio.research.search_ddgs", lambda query, max_results=2: [
        {"href": f"https://example.com/robots/{index}", "title": f"Robots {index}", "body": "x" * 5000}
        for index in range(12)
    ])
    sources = await research_queries("inline://text", ["ocean robots"], timeout=1)
    assert len(sources) == 8
    assert all(len(source.content) <= 4000 for source in sources)
    assert sum(len(source.content) for source in sources) == 24000


@pytest.mark.asyncio
async def test_url_research_preserves_primary_source_title(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr("app.studio.research.search_ddgs", lambda query, max_results=2: [])
    sources = await research_url("https://acme.example", "Acme AI", timeout=1)
    assert sources[0].title == "Acme AI"
    assert sources[0].claim == "Primary source supplied by the user"


@pytest.mark.asyncio
async def test_failed_url_research_report_retains_supplied_evidence(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr("app.studio.research.search_ddgs", lambda query, max_results=2: [])
    bundle = SourceBundle(
        kind="url",
        title="Acme AI",
        source_url="https://acme.example",
        dom_copy="Acme robots inspect underwater hulls.",
        palette=[],
        fonts=[],
        assets=[],
        citations=[],
        scroll_video=Path(),
    )
    plan = fallback_research_plan(bundle, "deep_dive")
    sources = await research_queries(bundle.source_url, plan.queries, timeout=1)
    report = fallback_research_report(bundle, plan, sources)
    assert sources == []
    assert report.summary == "Acme robots inspect underwater hulls."
    assert report.external_research is False


@pytest.mark.asyncio
async def test_inline_research_does_not_invent_primary_source(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr("app.studio.research.search_ddgs", lambda query, max_results=2: [])
    assert await research_queries("inline://text", ["ocean robots"], timeout=1) == []
