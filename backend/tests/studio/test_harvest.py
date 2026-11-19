from pathlib import Path

import pytest

from app.studio.harvest import harvest
from app.studio.urls import sample_site_url, validate_public_url


@pytest.mark.parametrize("value", [
    "ftp://example.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://user:pass@example.com",
    "http://10.0.0.1",
    "http://192.168.1.4",
])
@pytest.mark.asyncio
async def test_invalid_or_private_urls_are_rejected(value):
    with pytest.raises(ValueError):
        await validate_public_url(value)


@pytest.mark.asyncio
async def test_public_https_url_is_accepted():
    assert await validate_public_url("https://example.com") == "https://example.com"


@pytest.mark.asyncio
async def test_local_sample_site_is_harvested(tmp_path: Path):
    result = await harvest(sample_site_url(), tmp_path)
    assert "Orbit" in result.title
    assert "notes" in result.dom_copy.lower()
    assert result.palette
    assert result.fonts
    assert len(result.screenshots) == 2
    assert all(path.exists() for path in result.screenshots)
    assert result.scroll_video.exists()
    assert result.scroll_video.stat().st_size > 1000
    assert len(result.assets) >= 3


@pytest.mark.asyncio
async def test_page_settle_waits_for_network_fonts_and_entrance_motion():
    from app.studio.harvest import settle_page

    class FakePage:
        def __init__(self):
            self.calls = []

        async def wait_for_load_state(self, state, timeout):
            self.calls.append(("load", state, timeout))

        async def evaluate(self, script):
            self.calls.append(("evaluate", script))

        async def wait_for_timeout(self, milliseconds):
            self.calls.append(("wait", milliseconds))

    page = FakePage()
    await settle_page(page)
    assert ("load", "networkidle", 10000) in page.calls
    assert ("evaluate", "document.fonts.ready") in page.calls
    assert ("wait", 1800) in page.calls
