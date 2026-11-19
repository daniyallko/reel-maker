import asyncio
import ipaddress
import mimetypes
import re
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path
from urllib.parse import unquote, urlparse

SAMPLE_SITE = Path(__file__).resolve().parents[2] / "assets" / "link2reel" / "sample-site" / "index.html"


def sample_site_url() -> str:
    return SAMPLE_SITE.as_uri()


def is_global_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return address.is_global


async def validate_public_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Enter a public http or https URL")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL must not contain credentials or a missing hostname")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Private or local hosts are not allowed")
    try:
        address = ipaddress.ip_address(host)
        if not is_global_address(address):
            raise ValueError("Private or reserved IP addresses are not allowed")
    except ValueError as error:
        if "not allowed" in str(error):
            raise
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, ValueError) as error:
        raise ValueError("URL host could not be resolved") from error
    for entry in addresses:
        address = ipaddress.ip_address(entry[4][0].split("%", 1)[0])
        if not is_global_address(address):
            raise ValueError("URL resolves to a private or reserved address")
    return value.strip()


def allow_offline_url(url: str, project_dir: Path) -> bool:
    if url.startswith(("data:", "blob:", "about:")):
        return True
    if not url.startswith("file://"):
        return False
    path = Path(unquote(urlparse(url).path)).resolve()
    root = project_dir.resolve()
    return path == root or root in path.parents


def localize_motion_html(html: str, project_dir: Path, base_url: str) -> str:
    root = project_dir.resolve()
    def replace(match: re.Match) -> str:
        url = match.group(0)
        if not allow_offline_url(url, root):
            return "about:blank"
        relative = Path(unquote(urlparse(url).path)).resolve().relative_to(root)
        return f"{base_url}/{relative}"
    return re.sub(r"file://[^\"'\s<>]+", replace, html)


class LocalAssetServer:
    def __init__(self, project_dir: Path):
        self.root = project_dir.resolve()
        handler = partial(SimpleHTTPRequestHandler, directory=str(self.root))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


async def configure_offline_page(page, project_dir: Path) -> LocalAssetServer:
    server = LocalAssetServer(project_dir)
    root = project_dir.resolve()
    async def guard(route):
        url = route.request.url
        if url.startswith("file://"):
            if allow_offline_url(url, root):
                relative = Path(unquote(urlparse(url).path)).resolve().relative_to(root)
                await route.continue_(url=f"{server.base_url}/{relative}")
            else:
                await route.abort()
        elif url.startswith(("data:", "blob:", "about:", f"{server.base_url}/")):
            await route.continue_()
        else:
            await route.abort()
    await page.route("**/*", guard)
    return server
