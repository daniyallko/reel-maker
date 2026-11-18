import asyncio

import pytest
from PIL import Image

from app.events import EventBus
from app.media.prefilter import prefilter_assets
from app.schemas import EDLSegment, Genre, TrailerEDL
from app.validation import UploadValidationError, validate_upload, validate_upload_count


def test_upload_accepts_supported_types_and_rejects_path_traversal():
    assert validate_upload("photo.jpg", "image/jpeg", 100) == "photo"
    assert validate_upload("clip.mp4", "video/mp4", 100) == "video"
    with pytest.raises(UploadValidationError):
        validate_upload("../photo.jpg", "image/jpeg", 100)


def test_upload_count_and_size_are_bounded():
    with pytest.raises(UploadValidationError):
        validate_upload_count(9)
    with pytest.raises(UploadValidationError):
        validate_upload("large.png", "image/png", 26 * 1024 * 1024)


def test_prefilter_deduplicates_blurs_and_resizes(photo_input_factory):
    first = photo_input_factory("first.jpg", seed=3)
    duplicate = photo_input_factory("duplicate.jpg", seed=3)
    blurred = photo_input_factory("blurred.jpg", seed=8, blur=True)
    assets = prefilter_assets(first.path.parent, [first, duplicate, blurred])
    assert assets[0].kept is False  # Curation happens after local filtering.
    assert assets[0].rejection_reason is None
    assert max(Image.open(assets[0].perception_path).size) <= 768
    assert assets[1].rejection_reason == "Duplicate burst frame"
    assert assets[2].rejection_reason == "Too soft to survive the edit"


def test_corrupt_image_is_rejected_not_raised(tmp_path):
    path = tmp_path / "corrupt.jpg"
    path.write_bytes(b"not a real jpeg")
    from app.schemas import AssetInput
    assets = prefilter_assets(tmp_path, [AssetInput(filename=path.name, content_type="image/jpeg", path=path, size=path.stat().st_size)])
    assert assets[0].status == "rejected"
    assert assets[0].rejection_reason


def test_edl_requires_contiguous_timeline():
    with pytest.raises(ValueError, match="contiguous"):
        TrailerEDL(
            title="Test",
            tagline="Test",
            duration=22,
            genre=Genre.COMEDY,
            cast=[],
            segments=[EDLSegment(asset_id="a", act=1, start=1, end=22)],
        )


def test_event_bus_replays_ordered_events():
    async def scenario():
        bus = EventBus("project")
        await bus.emit("editor", "running", "First", 20)
        await bus.emit("editor", "complete", "Second", 100)
        await bus.close()
        received = []
        async for event in bus.stream(after_id=1):
            if event is not None:
                received.append(event)
        assert [event.id for event in received] == [2]
        assert received[0].message == "Second"
    asyncio.run(scenario())
