from pathlib import Path

import pytest

from app.studio.graph import merge_source_bundle, requires_web_harvest
from app.studio.schemas import SourceBundle, SourceCitation, StudioAsset
from app.studio.sources import ingest_text


def test_text_source_skips_web_harvest_and_preserves_citations():
    bundle = ingest_text("A text-only documentary about ocean repair.")
    assert requires_web_harvest(bundle) is False
    assert bundle.citations[0].url == "inline://text"


def test_url_bundle_merges_uploaded_assets_and_text(tmp_path: Path):
    primary = SourceBundle(
        kind="url",
        title="Primary",
        source_url="https://example.com",
        dom_copy="Website copy",
        palette=["#000000"],
        fonts=[],
        assets=[],
        screenshots=[tmp_path / "hero.png"],
        scroll_video=Path("video.webm"),
    )
    image = StudioAsset(id="upload-1", kind="image", label="CV image", url="/media/demo/uploads/cv.png", mime_type="image/png", local_path=tmp_path / "cv.png")
    uploaded = SourceBundle(
        kind="mixed",
        title="Mixed",
        source_url="https://example.com",
        dom_copy="Uploaded copy",
        palette=[],
        fonts=[],
        assets=[image],
        citations=[SourceCitation(url="inline://uploads", title="Upload", claim="Uploaded copy")],
        image_paths=[tmp_path / "cv.png"],
        scroll_video=Path(),
    )
    merged = merge_source_bundle(primary, uploaded)
    assert "Website copy" in merged.dom_copy
    assert "Uploaded copy" in merged.dom_copy
    assert merged.assets == [image]
    assert merged.image_paths == [tmp_path / "cv.png"]
    assert merged.citations[0].url == "inline://uploads"
    assert requires_web_harvest(merged) is True


@pytest.mark.asyncio
async def test_sample_research_preserves_replay_without_external_retrieval(monkeypatch, tmp_path):
    from app.studio.graph import research_bundle

    sample = ingest_text("Sample evidence").model_copy(update={"kind": "sample", "source_url": "https://sample.example"})

    async def fake_harvest(url, project_dir):
        return sample

    async def unexpected_queries(*args, **kwargs):
        raise AssertionError("sample replay must not retrieve external research")

    class Provider:
        async def plan_research(self, harvest, style):
            raise AssertionError("sample replay must not call Gemini planning")

    monkeypatch.setattr("app.studio.graph.harvest", fake_harvest)
    monkeypatch.setattr("app.studio.graph.research_queries", unexpected_queries)
    harvested, report = await research_bundle(Provider(), None, sample.source_url, tmp_path, sample=True)
    assert harvested == sample
    assert report.provider == "deterministic"
    assert report.external_research is False
    assert report.summary == "Sample evidence"
