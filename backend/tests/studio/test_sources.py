import io
from pathlib import Path

import pytest
from PIL import Image

from app.studio.schemas import SourceBundle
from app.studio.graph import requires_web_harvest
from app.studio.jobs import StudioJobManager
from app.config import Settings
from app.studio.sources import (
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_TEXT_CHARS,
    MAX_TOTAL_BYTES,
    ingest_text,
    ingest_uploads,
)


def test_text_source_needs_no_public_url():
    bundle = ingest_text("Build a reel about resilient space habitats.")
    assert isinstance(bundle, SourceBundle)
    assert bundle.kind == "text"
    assert bundle.source_url == "inline://text"
    assert "space habitats" in bundle.dom_copy
    assert bundle.citations[0].url == "inline://text"


def test_text_source_rejects_empty_and_excess_characters():
    with pytest.raises(ValueError, match="Enter a topic"):
        ingest_text("  ")
    with pytest.raises(ValueError, match="30,000"):
        ingest_text("x" * (MAX_TEXT_CHARS + 1))


def test_txt_upload_extracts_text(tmp_path: Path):
    text, assets, image_paths = ingest_uploads([
        ("notes.txt", "text/plain", b"Evidence from a text file."),
    ], tmp_path)
    assert text == "Evidence from a text file."
    assert assets == []
    assert image_paths == []


def pdf_bytes(text: str) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject()
    font.update({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_upload_extracts_text(tmp_path: Path):
    text, assets, _ = ingest_uploads([
        ("cv.pdf", "application/pdf", pdf_bytes("Portfolio evidence")),
    ], tmp_path)
    assert "Portfolio evidence" in text
    assert assets == []


def test_bad_pdf_and_mime_are_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="valid PDF"):
        ingest_uploads([("bad.pdf", "application/pdf", b"not a pdf")], tmp_path)
    with pytest.raises(ValueError, match="Unsupported file"):
        ingest_uploads([("notes.pdf", "text/plain", b"plain")], tmp_path)


def test_images_become_source_assets(tmp_path: Path):
    files = []
    for extension, mime, image_format in (("png", "image/png", "PNG"), ("jpg", "image/jpeg", "JPEG"), ("webp", "image/webp", "WEBP")):
        output = io.BytesIO()
        Image.new("RGB", (32, 48), "#182030").save(output, image_format)
        files.append((f"visual.{extension}", mime, output.getvalue()))
    _, assets, image_paths = ingest_uploads(files, tmp_path)
    assert len(assets) == 3
    assert len(image_paths) == 3
    assert all(asset.kind == "image" and asset.local_path.exists() for asset in assets)
    assert all(asset.local_path.is_relative_to(tmp_path) for asset in assets)


def test_upload_count_and_size_limits(tmp_path: Path):
    with pytest.raises(ValueError, match="8 files"):
        ingest_uploads([("notes.txt", "text/plain", b"x")] * (MAX_FILES + 1), tmp_path)
    with pytest.raises(ValueError, match="10 MB"):
        ingest_uploads([("large.txt", "text/plain", b"x" * (MAX_FILE_BYTES + 1))], tmp_path)
    with pytest.raises(ValueError, match="30 MB"):
        ingest_uploads([
            ("one.txt", "text/plain", b"x" * MAX_FILE_BYTES),
            ("two.txt", "text/plain", b"x" * MAX_FILE_BYTES),
            ("three.txt", "text/plain", b"x" * MAX_FILE_BYTES),
            ("four.txt", "text/plain", b"x"),
        ], tmp_path)
    assert MAX_TOTAL_BYTES == 30 * 1024 * 1024


def image_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 48), "#182030").save(output, "PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_image_only_bundle_preserves_visual_evidence(tmp_path: Path, monkeypatch):
    manager = StudioJobManager(Settings(data_dir=tmp_path))
    async def no_run(*_):
        return None
    monkeypatch.setattr(manager, "_run", no_run)
    snapshot = await manager.create_input("", "launch", "Fenrir", [("evidence.png", "image/png", image_bytes())])
    bundle = manager.get(snapshot.id).source_bundle
    assert "1 source image" in bundle.dom_copy
    assert "evidence.png" in bundle.dom_copy
    assert bundle.citations[0].url == "inline://images"
    assert "evidence.png" in bundle.citations[0].claim


@pytest.mark.asyncio
async def test_url_uploads_have_traceable_citations(tmp_path: Path, monkeypatch):
    manager = StudioJobManager(Settings(data_dir=tmp_path))
    async def no_run(*_):
        return None
    async def fake_validate(value):
        return value
    monkeypatch.setattr(manager, "_run", no_run)
    monkeypatch.setattr("app.studio.jobs.validate_public_url", fake_validate)
    snapshot = await manager.create_input("https://example.com", "launch", "Fenrir", [("claim.txt", "text/plain", b"Unique uploaded claim")])
    bundle = manager.get(snapshot.id).source_bundle
    assert any(citation.url == "inline://uploads" and "Unique uploaded claim" in citation.claim for citation in bundle.citations)


@pytest.mark.asyncio
async def test_uppercase_http_url_remains_a_web_source(tmp_path: Path, monkeypatch):
    manager = StudioJobManager(Settings(data_dir=tmp_path))
    async def no_run(*_):
        return None
    async def fake_validate(value):
        return value
    monkeypatch.setattr(manager, "_run", no_run)
    monkeypatch.setattr("app.studio.jobs.validate_public_url", fake_validate)
    snapshot = await manager.create_input("HTTPS://example.com", "launch", "Fenrir", [])
    bundle = manager.get(snapshot.id).source_bundle
    assert bundle.kind == "url"
    assert requires_web_harvest(bundle) is True
