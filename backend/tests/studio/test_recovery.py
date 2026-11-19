from app.schemas import ProjectStatus
from app.studio.api import manager
from app.studio.providers import mock_storyboard
from app.studio.schemas import StudioOutput


def test_completed_project_restores_from_disk(tmp_path):
    storyboard = mock_storyboard("launch", "Fenrir")
    output = StudioOutput(
        title=storyboard.title,
        trailer_url="/media/demo/output/trailer.mp4",
        thumbnail_url="/media/demo/visuals/thumbnail-03.png",
        preview_url="/media/demo/audio/narration.wav",
        duration=35,
        bpm=128,
        scenes=storyboard.scenes,
        sources=storyboard.sources,
        script="Script",
        source_url="https://acme.example",
        style="launch",
        voice="Fenrir",
    )
    output_dir = tmp_path / "demo" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "studio-output.json").write_text(output.model_dump_json())
    original_dir = manager.settings.data_dir
    manager.settings.data_dir = tmp_path
    manager.jobs.clear()
    try:
        restored = manager.get("demo")
        assert restored.status == ProjectStatus.COMPLETE
        assert restored.output.title == storyboard.title
        assert restored.source_url == "https://acme.example"
    finally:
        manager.settings.data_dir = original_dir
        manager.jobs.clear()
