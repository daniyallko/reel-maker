from pathlib import Path

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
