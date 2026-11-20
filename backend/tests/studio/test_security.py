import ipaddress
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from app.studio.harvest import validate_image_bytes
from app.studio.motion import generate_motion_html
from app.studio.urls import is_global_address, validate_public_url
from app.studio.vision import VisionDirector


def test_audit_frame_contains_visible_scene():
    path = Path(__file__).parents[2] / "assets" / "link2reel" / "sample-output" / "audit" / "frame-01-1.000.png"
    image = Image.open(path).convert("RGB")
    assert sum(ImageStat.Stat(image).mean) > 60, "Frame is mostly blank"


def test_private_dns_result_is_rejected():
    assert not is_global_address(ipaddress.ip_address("127.0.0.1"))
    assert not is_global_address(ipaddress.ip_address("169.254.169.254"))
    assert is_global_address(ipaddress.ip_address("93.184.216.34"))


@pytest.mark.asyncio
async def test_url_validation_resolves_dns(monkeypatch):
    import socket
    def fake_resolution(*_):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    monkeypatch.setattr(socket, "getaddrinfo", fake_resolution)
    with pytest.raises(ValueError):
        await validate_public_url("https://rebound.example")


def test_image_validation_rejects_invalid_and_oversized():
    with pytest.raises(ValueError):
        validate_image_bytes(b"not an image")
    with pytest.raises(ValueError):
        validate_image_bytes(b"x" * (10 * 1024 * 1024 + 1))


@pytest.mark.asyncio
async def test_invalid_clock_uses_deterministic_fallback(tmp_path: Path):
    from types import SimpleNamespace
    from app.studio.providers import fallback_visuals, mock_storyboard
    storyboard = mock_storyboard("launch", "Fenrir")
    assets = fallback_visuals(storyboard, None, tmp_path)
    provider = SimpleNamespace(
        client=SimpleNamespace(
            models=SimpleNamespace(
                generate_content=lambda **_: SimpleNamespace(text="<script>window.seekTo = 1</script>")
            )
        )
    )
    html = await generate_motion_html(storyboard, assets, provider=provider, project_dir=tmp_path)
    assert "const scenes" in html


@pytest.mark.asyncio
async def test_vision_patch_is_sanitized():
    from types import SimpleNamespace
    from app.studio.vision import VisionAudit
    audit = VisionAudit(passed=False, issues=["external code"], patched_html="<script src='https://evil.example/x.js'></script><script>window.seekTo=t=>t</script>")
    client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **_: SimpleNamespace(parsed=audit)
        )
    )
    path = Path(__file__).parents[2] / "assets" / "link2reel" / "sample-output" / "audit" / "contact-sheet.png"
    result = await VisionDirector(client).audit(path, "<script>window.seekTo=t=>t</script>")
    assert "evil.example" not in result.patched_html
