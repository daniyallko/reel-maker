import io
from pathlib import Path

from PIL import Image

from app.studio.schemas import SourceBundle, SourceCitation, StudioAsset

MAX_FILES = 8
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 30 * 1024 * 1024
MAX_TEXT_CHARS = 30_000
MAX_IMAGE_PIXELS = 40_000_000


def _title_for(text: str) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "Untitled story")
    return first_line[:80]


def ingest_text(text: str, title: str | None = None) -> SourceBundle:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Enter a topic, description, URL, or source file.")
    if len(cleaned) > MAX_TEXT_CHARS:
        raise ValueError("Source text must contain at most 30,000 characters.")
    source_title = title or _title_for(cleaned)
    return SourceBundle(
        kind="text",
        title=source_title,
        source_url="inline://text",
        dom_copy=cleaned,
        palette=[],
        fonts=[],
        assets=[],
        citations=[SourceCitation(url="inline://text", title=source_title, claim=cleaned[:240])],
        scroll_video=Path(),
    )


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages).strip()
    except Exception as error:
        raise ValueError("Upload a valid PDF with extractable text.") from error


def ingest_uploads(files: list[tuple[str, str, bytes]], project_dir: Path) -> tuple[str, list[StudioAsset], list[Path]]:
    if len(files) > MAX_FILES:
        raise ValueError("Upload at most 8 files.")
    if sum(len(data) for _, _, data in files) > MAX_TOTAL_BYTES:
        raise ValueError("Uploaded files must total at most 30 MB.")
    upload_dir = project_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    texts: list[str] = []
    assets: list[StudioAsset] = []
    image_paths: list[Path] = []
    allowed = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    for index, (filename, content_type, data) in enumerate(files, start=1):
        suffix = Path(filename).suffix.lower()
        if suffix not in allowed or content_type.split(";", 1)[0].strip().lower() != allowed[suffix]:
            raise ValueError(f"Unsupported file: {Path(filename).name}")
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Each uploaded file must be at most 10 MB.")
        if suffix == ".pdf":
            texts.append(_pdf_text(data))
        elif suffix == ".txt":
            try:
                texts.append(data.decode("utf-8").strip())
            except UnicodeDecodeError as error:
                raise ValueError("TXT files must use UTF-8 encoding.") from error
        else:
            try:
                with Image.open(io.BytesIO(data)) as image:
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise ValueError("Images must contain at most 40 million pixels.")
                    image.verify()
            except ValueError:
                raise
            except Exception as error:
                raise ValueError(f"Upload a valid image: {Path(filename).name}") from error
            safe_name = Path(filename).name
            path = upload_dir / f"{index:02d}-{safe_name}"
            path.write_bytes(data)
            image_paths.append(path)
            assets.append(StudioAsset(
                id=f"upload-{index}",
                kind="image",
                label=safe_name,
                url=f"/media/{project_dir.name}/uploads/{path.name}",
                mime_type=content_type,
                local_path=path,
            ))
    combined = "\n\n".join(text for text in texts if text).strip()
    if len(combined) > MAX_TEXT_CHARS:
        raise ValueError("Extracted text must contain at most 30,000 characters.")
    return combined, assets, image_paths
