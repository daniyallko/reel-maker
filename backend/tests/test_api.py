from fastapi.testclient import TestClient

from app.api import manager, settings
from app.main import app
from app.schemas import Genre, ProjectSnapshot, ProjectStatus


def fake_snapshot(project_id):
    return ProjectSnapshot(id=project_id, status=ProjectStatus.QUEUED, genre=Genre.COMEDY, created_at=1)


def test_same_named_uploads_get_unique_storage_paths(monkeypatch):
    captured = {}
    async def fake_create(project_id, inputs, cast, genre, notes, voice_path, sample=False):
        captured["inputs"] = inputs
        return fake_snapshot(project_id)
    monkeypatch.setattr(manager, "create", fake_create)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "mock_mode", False)
    files = [("files", ("IMG_0001.jpg", f"image-{index}".encode(), "image/jpeg")) for index in range(10)]
    response = TestClient(app).post("/api/projects", files=files, data={"cast": "Maya", "genre": "comedy", "notes": ""})
    assert response.status_code == 202, response.text
    inputs = captured["inputs"]
    assert len({item.path.name for item in inputs}) == 10
    assert all(item.filename == "IMG_0001.jpg" for item in inputs)


def test_safari_voice_note_keeps_mp4_mime(monkeypatch):
    captured = {}
    async def fake_create(project_id, inputs, cast, genre, notes, voice_path, sample=False):
        captured["voice"] = voice_path
        return fake_snapshot(project_id)
    monkeypatch.setattr(manager, "create", fake_create)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "mock_mode", False)
    files = [("files", (f"photo-{index}.jpg", b"image", "image/jpeg")) for index in range(10)]
    files.append(("voice_note", ("note.m4a", b"audio", "audio/mp4")))
    response = TestClient(app).post("/api/projects", files=files, data={"cast": "Maya", "genre": "comedy", "notes": ""})
    assert response.status_code == 202, response.text
    assert captured["voice"].suffix == ".mp4"


def test_real_upload_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "mock_mode", False)
    response = TestClient(app).post(
        "/api/projects",
        files=[("files", ("photo.jpg", b"image", "image/jpeg"))],
        data={"cast": "Maya", "genre": "comedy"},
    )
    assert response.status_code == 503
    assert "Sample mode" in response.json()["detail"]
