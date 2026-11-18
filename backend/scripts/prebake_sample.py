import asyncio
from pathlib import Path

from app.events import EventBus
from app.graph import build_graph
from app.media.audio import AudioProducer
from app.media.editor import VideoEditor
from app.media.poster import PosterArtDirector
from app.media.prefilter import prefilter_assets
from app.providers.mock import MockPerceptionProvider, MockScreenwriterProvider
from app.schemas import AssetInput, Genre

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "assets" / "sample"


async def main():
    inputs = [
        AssetInput(
            filename=path.name,
            content_type="image/jpeg",
            path=path,
            size=path.stat().st_size,
        )
        for path in sorted((SAMPLE / "uploads").glob("*.jpg"))
    ]
    assets = prefilter_assets(SAMPLE, inputs)
    events = EventBus("sample")
    graph = build_graph(
        MockPerceptionProvider(),
        MockScreenwriterProvider(),
        PosterArtDirector(use_rembg=False),
        AudioProducer(),
        VideoEditor(),
        sample=True,
    )
    result = await graph.ainvoke(
        {
            "project_id": "sample",
            "project_dir": SAMPLE,
            "assets": assets,
            "cast": ["Maya", "Theo", "Nina", "Jules"],
            "genre": Genre.COMEDY,
            "notes": "Nobody admits who booked the house.",
            "voice_path": None,
            "events": events,
        }
    )
    output = result["output"]
    (SAMPLE / "output" / "press-kit.json").write_text(
        output.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"Pre-baked sample trailer, poster, and {len(output.cast_cards)} cast cards.")


if __name__ == "__main__":
    asyncio.run(main())
