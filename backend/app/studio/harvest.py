import io
import shutil
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx
from PIL import Image
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.studio.schemas import HarvestResult, StudioAsset
from app.studio.urls import validate_public_url

MAX_IMAGE_BYTES = 10 * 1024 * 1024


def media_url(project_dir: Path, path: Path) -> str:
    return f"/media/{project_dir.name}/{path.relative_to(project_dir)}"


def validate_image_bytes(data: bytes) -> None:
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds the 10 MB source limit")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as error:
        raise ValueError("Downloaded file is not a valid image") from error


async def configure_harvest_page(page) -> None:
    async def guard(route):
        url = route.request.url
        if url.startswith(("file://", "data:", "blob:", "about:")):
            await route.continue_()
            return
        try:
            await validate_public_url(url)
            await route.continue_()
        except (ValueError, httpx.HTTPError):
            await route.abort()
    await page.route("**/*", guard)


async def download_image(client: httpx.AsyncClient, url: str) -> bytes:
    current = url
    for _ in range(5):
        await validate_public_url(current)
        response = await client.get(current, follow_redirects=False)
        if response.is_redirect:
            current = urljoin(current, response.headers["location"])
            continue
        response.raise_for_status()
        length = int(response.headers.get("content-length", "0") or 0)
        if length > MAX_IMAGE_BYTES:
            raise ValueError("Image exceeds the 10 MB source limit")
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ValueError("Source URL is not an image")
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise ValueError("Image exceeds the 10 MB source limit")
            chunks.append(chunk)
        data = b"".join(chunks)
        validate_image_bytes(data)
        return data
    raise ValueError("Image redirect limit exceeded")


async def settle_page(page) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass
    await page.evaluate("document.fonts.ready")
    await page.wait_for_timeout(1800)


async def harvest(url: str, project_dir: Path) -> HarvestResult:
    capture_dir = project_dir / "harvest"
    video_dir = project_dir / "video"
    capture_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    screenshots = [capture_dir / "hero.png", capture_dir / "mid.png"]
    image_paths: list[Path] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1080, "height": 1920},
        )
        page = await context.new_page()
        await configure_harvest_page(page)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        if not page.url.startswith("file://"):
            await validate_public_url(page.url)
        await settle_page(page)
        title = await page.title()
        copy = await page.locator("body").inner_text()
        design = await page.evaluate("""() => {
          const colors = new Set(), fonts = new Set();
          for (const element of document.querySelectorAll('body, h1, h2, p, a, button, section')) {
            const style = getComputedStyle(element);
            colors.add(style.color); colors.add(style.backgroundColor);
            fonts.add(style.fontFamily);
          }
          return {colors: [...colors].filter(Boolean), fonts: [...fonts].filter(Boolean)};
        }""")
        await page.screenshot(path=str(screenshots[0]), full_page=False)
        image_urls = await page.locator("img").evaluate_all("images => images.map(image => image.currentSrc || image.src).filter(Boolean)")
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            for index, image_url in enumerate(image_urls[:3]):
                destination = capture_dir / f"site-image-{index + 1}.jpg"
                try:
                    if image_url.startswith("file://"):
                        source = Path(unquote(urlparse(image_url).path))
                        if source.exists() and source.stat().st_size <= MAX_IMAGE_BYTES:
                            validate_image_bytes(source.read_bytes())
                            shutil.copy2(source, destination)
                            image_paths.append(destination)
                    elif image_url.startswith(("http://", "https://")):
                        data = await download_image(client, image_url)
                        destination.write_bytes(data)
                        image_paths.append(destination)
                except (OSError, ValueError, httpx.HTTPError):
                    continue
        await page.evaluate("window.scrollTo({top: document.body.scrollHeight * 0.45, behavior: 'instant'})")
        await page.wait_for_timeout(1800)
        await page.screenshot(path=str(screenshots[1]), full_page=False)
        await page.evaluate("""() => new Promise(resolve => {
          const start = performance.now();
          const duration = 4000;
          const distance = Math.max(0, document.body.scrollHeight - innerHeight);
          function step(now) {
            const progress = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - progress, 3);
            window.scrollTo(0, distance * eased);
            if (progress < 1) requestAnimationFrame(step); else resolve();
          }
          requestAnimationFrame(step);
        })""")
        video_path = Path(await page.video.path())
        await context.close()
        await browser.close()

    assets = [
        StudioAsset(id="hero", kind="screenshot", label="Hero capture", url=media_url(project_dir, screenshots[0]), mime_type="image/png", local_path=screenshots[0]),
        StudioAsset(id="mid", kind="screenshot", label="Mid-page capture", url=media_url(project_dir, screenshots[1]), mime_type="image/png", local_path=screenshots[1]),
        StudioAsset(id="scroll", kind="video", label="4-second site scroll", url=media_url(project_dir, video_path), mime_type="video/webm", local_path=video_path),
    ]
    for index, path in enumerate(image_paths, start=1):
        assets.append(StudioAsset(id=f"site-{index}", kind="image", label=f"Site image {index}", url=media_url(project_dir, path), mime_type="image/jpeg", local_path=path))
    return HarvestResult(
        source_url=url,
        title=title,
        palette=design["colors"],
        fonts=design["fonts"],
        dom_copy=copy[:18000],
        assets=assets,
        screenshots=screenshots,
        scroll_video=video_path,
        image_paths=image_paths,
    )
