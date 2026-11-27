from unittest.mock import AsyncMock

import pytest

from app.studio.eclipse import eclipse_board
from app.studio.motion import fallback_motion_html, generate_motion_html
from app.studio.providers import GeminiStudioProvider
from app.studio.renderer import write_ass_captions
from app.studio.sources import ingest_text


@pytest.mark.asyncio
async def test_director_rewrites_overlong_script_and_authors_motion(tmp_path):
    brief = ingest_text("Explain a total solar eclipse.")
    board = eclipse_board(brief.citations, "deep_dive", "Fenrir")
    long = board.model_copy(deep=True)
    long.scenes[0].narration = "word " * 100
    provider = object.__new__(GeminiStudioProvider)
    provider.director_model = "test-director"
    provider.direct = AsyncMock(side_effect=[long.model_dump_json(), board.model_dump_json(),
                                             "<html><script>window.seekTo=t=>{};</script></html>"])
    plan = await provider.write_storyboard(brief, brief.citations, "deep_dive", "Fenrir")
    assert plan.directed_motion
    assert provider.direct.await_count == 2
    plan.scenes[0].id = "custom-hook"
    assert "window.seekTo" in await generate_motion_html(plan, [], provider)
    assert provider.direct.await_count == 3
    captions = write_ass_captions(plan, [4]*4, tmp_path / "captions.ass").read_text()
    assert "Style: Default" in captions
    assert "See that shadow racing" in captions


def test_eclipse_draft_repair_preserves_subject():
    brief = ingest_text("Solar eclipse")
    board = eclipse_board(brief.citations, "deep_dive", "Fenrir")
    html = fallback_motion_html(board, [])
    assert "earth(" in html and "PARTIAL" in html and "TOTAL" in html
