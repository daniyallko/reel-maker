from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image
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


@pytest.mark.asyncio
async def test_text_only_graph_researches_and_synthesizes(monkeypatch, tmp_path):
    from app.studio.graph import research_bundle

    bundle = ingest_text("Ocean cleanup robots")
    seen = []
    styles = []

    async def fake_queries(url, queries, timeout=10):
        seen.extend(queries)
        return [SourceCitation(url="https://example.com/ocean", title="Ocean evidence", claim="Robots collect plastic", content="Robots collect plastic")]

    class Provider:
        async def plan_research(self, harvest, style):
            styles.append(style)
            return ResearchPlan(topic=harvest.title, angle="Systems", queries=["ocean cleanup robots"])

        async def synthesize_research(self, harvest, plan, sources):
            return fallback_research_report(harvest, plan, sources).model_copy(update={"provider": "gemini"})

    monkeypatch.setattr("app.studio.graph.research_queries", fake_queries)
    harvested, report = await research_bundle(Provider(), bundle, bundle.source_url, tmp_path, style="founder")
    assert seen == ["ocean cleanup robots"]
    assert styles == ["founder"]
    assert report.provider == "gemini"
    assert report.external_research is True


@pytest.mark.asyncio
async def test_url_research_plans_from_original_brief_and_merges_uploaded_evidence(monkeypatch, tmp_path):
    from app.studio.graph import research_bundle

    bundle = SourceBundle(
        kind="url",
        title="https://acme.example",
        source_url="https://acme.example",
        dom_copy="Uploaded robot notes",
        palette=[],
        fonts=[],
        assets=[],
        citations=[SourceCitation(url="inline://uploads", title="Upload", claim="Uploaded robot notes")],
        scroll_video=Path(),
    )
    website = SourceBundle(
        kind="url",
        title="Acme Robots",
        source_url="https://acme.example",
        dom_copy="Acme robots inspect hulls",
        palette=[],
        fonts=[],
        assets=[],
        citations=[SourceCitation(url="https://acme.example", title="Acme", claim="Acme robots inspect hulls")],
        scroll_video=Path(),
    )
    planned_from = []

    async def fake_harvest(url, project_dir):
        return website

    async def fake_queries(url, queries, timeout=10):
        return [SourceCitation(url="https://evidence.example/robots", title="Robot evidence", claim="Hull robots reduce inspection risk", content="Hull robots reduce inspection risk")]

    class Provider:
        async def plan_research(self, harvest, style):
            planned_from.append(harvest)
            return ResearchPlan(topic="Acme robots", angle=style, queries=["Acme robots"])

        async def synthesize_research(self, harvest, plan, sources):
            return fallback_research_report(harvest, plan, sources).model_copy(update={"provider": "gemini"})

    monkeypatch.setattr("app.studio.graph.harvest", fake_harvest)
    monkeypatch.setattr("app.studio.graph.research_queries", fake_queries)
    harvested, report = await research_bundle(Provider(), bundle, bundle.source_url, tmp_path)
    assert planned_from == [bundle]
    assert "Acme robots inspect hulls" in harvested.dom_copy
    assert "Uploaded robot notes" in harvested.dom_copy
    assert {source.url for source in report.sources} == {
        "https://acme.example",
        "inline://uploads",
        "https://evidence.example/robots",
    }
    assert report.external_research is True


@pytest.mark.asyncio
async def test_gemini_plan_research_uses_schema_fallback_timeout_and_four_images(monkeypatch, tmp_path):
    from app.studio.providers import CORE_MODEL, FALLBACK_MODEL, GeminiStudioProvider

    images = []
    for index in range(5):
        path = tmp_path / f"evidence-{index}.png"
        Image.new("RGB", (8, 8), "#182030").save(path)
        images.append(path)
    bundle = ingest_text("Ocean cleanup robots").model_copy(update={"image_paths": images})
    provider = GeminiStudioProvider("key")
    calls = []
    timeouts = []

    class Models:
        @staticmethod
        def generate_content(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("core unavailable")
            return SimpleNamespace(parsed=ResearchPlan(topic="Ocean cleanup robots", angle="Systems", queries=["ocean robots"]), text="")

    async def immediate(awaitable, timeout):
        timeouts.append(timeout)
        return await awaitable

    provider.client = SimpleNamespace(models=Models)
    monkeypatch.setattr("app.studio.providers.asyncio.wait_for", immediate)
    plan = await provider.plan_research(bundle, "deep_dive")
    assert plan.queries == ["ocean robots"]
    assert [call["model"] for call in calls] == [CORE_MODEL, FALLBACK_MODEL]
    assert timeouts == [90, 90]
    assert all(call["config"].response_schema is ResearchPlan for call in calls)
    assert all(len(call["contents"]) == 5 for call in calls)
    assert all(getattr(part, "inline_data", None) for part in calls[-1]["contents"][1:])


@pytest.mark.asyncio
async def test_gemini_synthesis_uses_supplied_sources_and_structured_report(monkeypatch, tmp_path):
    from app.studio.providers import CORE_MODEL, FALLBACK_MODEL, GeminiStudioProvider

    image = tmp_path / "evidence.png"
    Image.new("RGB", (8, 8), "#182030").save(image)
    bundle = ingest_text("Ocean cleanup robots").model_copy(update={"image_paths": [image]})
    plan = ResearchPlan(topic="Ocean cleanup robots", angle="Systems", queries=["ocean robots"])
    sources = [SourceCitation(url="https://example.com/ocean", title="Ocean evidence", claim="Robots collect plastic", content="Robots collect plastic")]
    parsed = ResearchReport(
        topic=plan.topic,
        angle=plan.angle,
        summary="Robots collect plastic",
        claims=[EvidenceClaim(text="Robots collect plastic", source_refs=[1])],
        sources=[bundle.citations[0], *sources],
        queries=plan.queries,
        external_research=False,
        provider="model-response",
    )
    provider = GeminiStudioProvider("key")
    calls = []
    timeouts = []

    class Models:
        @staticmethod
        def generate_content(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("core unavailable")
            return SimpleNamespace(parsed=parsed, text="")

    async def immediate(awaitable, timeout):
        timeouts.append(timeout)
        return await awaitable

    provider.client = SimpleNamespace(models=Models)
    monkeypatch.setattr("app.studio.providers.asyncio.wait_for", immediate)
    report = await provider.synthesize_research(bundle, plan, sources)
    assert report.provider == "gemini"
    assert report.sources == [bundle.citations[0], *sources]
    assert report.sources[1].content == "Robots collect plastic"
    assert report.external_research is True
    assert [call["model"] for call in calls] == [CORE_MODEL, FALLBACK_MODEL]
    assert timeouts == [90, 90]
    assert all(call["config"].response_schema is ResearchReport for call in calls)
    assert len(calls[-1]["contents"]) == 2
    assert "Robots collect plastic" in calls[-1]["contents"][0]


@pytest.mark.asyncio
async def test_invalid_gemini_research_responses_use_deterministic_fallbacks(tmp_path):
    from app.studio.providers import GeminiStudioProvider

    bundle = ingest_text("Ocean cleanup robots")
    plan = fallback_research_plan(bundle, "deep_dive")
    sources = [SourceCitation(url="https://example.com/ocean", title="Ocean evidence", claim="Robots collect plastic", content="Robots collect plastic")]
    provider = GeminiStudioProvider("key")

    class Models:
        @staticmethod
        def generate_content(**kwargs):
            return SimpleNamespace(parsed=None, text="not valid JSON")

    provider.client = SimpleNamespace(models=Models)
    actual_plan = await provider.plan_research(bundle, "deep_dive")
    report = await provider.synthesize_research(bundle, plan, sources)
    assert actual_plan == plan
    assert report == fallback_research_report(bundle, plan, sources)
    assert report.provider == "deterministic"
    assert report.external_research is True


@pytest.mark.asyncio
async def test_storyboard_accepts_optional_research_without_changing_legacy_arguments():
    from app.studio.providers import MockStudioProvider

    bundle = ingest_text("Ocean cleanup robots")
    plan = fallback_research_plan(bundle, "deep_dive")
    research = fallback_research_report(bundle, plan, [])
    storyboard = await MockStudioProvider().write_storyboard(None, [], "launch", "Fenrir", research=research)
    assert storyboard.duration == 32
