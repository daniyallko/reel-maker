from app.studio.providers import GeminiStudioProvider
from app.studio.schemas import HarvestResult, SourceCitation


async def test_live_storyboard_failure_uses_current_source_not_orbit():
    harvest = HarvestResult(
        source_url="https://acme.example",
        title="Acme Weather Maps",
        palette=[],
        fonts=[],
        dom_copy="Acme makes neighborhood weather maps for hikers.",
        assets=[],
        screenshots=[],
        scroll_video=__import__("pathlib").Path("unused"),
        image_paths=[],
    )
    sources = [SourceCitation(url="https://acme.example", title="Acme Weather Maps", claim="Neighborhood weather maps")]
    provider = GeminiStudioProvider("key")
    class FailingModels:
        @staticmethod
        def generate_content(**_):
            raise RuntimeError("rate limited")
    provider.client = type("Client", (), {"models": FailingModels})()
    storyboard = await provider.write_storyboard(harvest, sources, "launch", "Fenrir")
    assert "Acme" in storyboard.title
    assert storyboard.sources[0].url == "https://acme.example"
    assert "Orbit" not in storyboard.title
