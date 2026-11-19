from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.studio.api import manager
from app.studio.jobs import StudioJob
from app.studio.schemas import StudioProjectSnapshot
from app.studio.urls import sample_site_url


def test_invalid_url_returns_422():
    response = TestClient(app).post("/api/studio/projects", json={"url": "http://127.0.0.1:8000", "style": "launch", "voice": "Fenrir"})
    assert response.status_code == 422


def test_sample_route_uses_mock_mode(monkeypatch):
    called = {}
    async def fake_create(url, style, voice, sample=False, quality_mode="strict"):
        called.update(url=url, style=style, voice=voice, sample=sample)
        return StudioProjectSnapshot(id="studio-demo", status="queued", source_url=url, style=style, voice=voice, created_at=1)
    monkeypatch.setattr(manager, "create", fake_create)
    response = TestClient(app).post("/api/studio/projects/sample")
    assert response.status_code == 202
    assert response.json()["id"] == "studio-demo"
    assert called["sample"] is True
    assert called["voice"] == "Fenrir"


@pytest.mark.asyncio
async def test_sample_replay_asset_ids_are_unique():
    snapshot = await manager.create(sample_site_url(), "launch", "Fenrir", sample=True)
    job = manager.get(snapshot.id)
    await job.task
    ids = [asset.id for asset in job.assets]
    assert len(ids) == len(set(ids))


def test_zip_uses_generated_thumbnail_path(tmp_path):
    from app.events import EventBus
    from app.schemas import ProjectStatus
    from app.studio.providers import mock_storyboard
    from app.studio.schemas import StudioOutput
    storyboard = mock_storyboard("launch", "Fenrir")
    (tmp_path / "visuals").mkdir()
    (tmp_path / "visuals" / "visual-03.png").write_bytes(b"png")
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "trailer.mp4").write_bytes(b"mp4")
    output = StudioOutput(
        title=storyboard.title,
        trailer_url="/media/demo/output/trailer.mp4",
        thumbnail_url="/media/demo/visuals/visual-03.png",
        preview_url="/media/demo/audio/narration.wav",
        duration=35,
        bpm=128,
        scenes=storyboard.scenes,
        sources=storyboard.sources,
        script="Script",
    )
    manager.jobs["demo"] = StudioJob(
        id="demo",
        source_url="https://example.com",
        style="launch",
        voice="Fenrir",
        directory=tmp_path,
        events=EventBus("demo"),
        status=ProjectStatus.COMPLETE,
        output=output,
    )
    import zipfile
    with zipfile.ZipFile(manager.press_kit_zip("demo")) as archive:
        assert "thumbnail.png" in archive.namelist()


def test_user_domain_is_passed_through_unchanged(monkeypatch):
    captured = {}
    async def fake_create(url, style, voice, sample=False, quality_mode="strict"):
        captured["url"] = url
        return StudioProjectSnapshot(id="acme", status="queued", source_url=url, style=style, voice=voice, created_at=1)
    monkeypatch.setattr(manager, "create", fake_create)
    response = TestClient(app).post("/api/studio/projects", json={"url": "https://acme.example/products", "style": "launch", "voice": "Fenrir"})
    assert response.status_code == 202
    assert captured["url"] == "https://acme.example/products"


def test_project_and_event_routes_exist(monkeypatch):
    snapshot = StudioProjectSnapshot(id="studio-demo", status="queued", source_url="https://example.com", style="launch", voice="Fenrir", created_at=1)
    monkeypatch.setattr(manager, "get", lambda _: type("Job", (), {"snapshot": lambda self: snapshot, "events": object()})())
    response = TestClient(app).get("/api/studio/projects/studio-demo")
    assert response.status_code == 200
    assert response.json()["id"] == "studio-demo"


def test_multipart_source_endpoint_accepts_text_and_files(monkeypatch):
    called = {}

    async def fake_create_input(source, style, voice, files, quality_mode="strict"):
        called.update(source=source, style=style, voice=voice, files=files, quality_mode=quality_mode)
        return StudioProjectSnapshot(
            id="input-demo",
            status="queued",
            source_url="inline://text",
            source_title="A cinematic story",
            style=style,
            voice=voice,
            created_at=1,
        )

    monkeypatch.setattr(manager, "create_input", fake_create_input)
    response = TestClient(app).post(
        "/api/studio/projects/inputs",
        data={"source": "A cinematic story", "style": "tech_launch", "voice": "Aoede", "quality_mode": "draft"},
        files=[
            ("files", ("notes.txt", b"Evidence", "text/plain")),
            ("files", ("visual.png", b"png-bytes", "image/png")),
        ],
    )
    assert response.status_code == 202
    assert response.json()["source_title"] == "A cinematic story"
    assert called["source"] == "A cinematic story"
    assert called["quality_mode"] == "draft"
    assert called["files"][0][0] == "notes.txt"
    assert called["files"][1][1] == "image/png"


def test_multipart_source_endpoint_returns_public_validation_message(monkeypatch):
    async def invalid_source(*_, **__):
        raise ValueError("Enter a topic, description, URL, or source file.")

    monkeypatch.setattr(manager, "create_input", invalid_source)
    response = TestClient(app).post(
        "/api/studio/projects/inputs",
        data={"source": "", "style": "launch", "voice": "Fenrir"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Enter a topic, description, URL, or source file."
