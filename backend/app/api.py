import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.config import get_settings
from app.jobs import JobManager
from app.schemas import AssetInput, Genre
from app.validation import UploadValidationError, validate_upload, validate_upload_count

router = APIRouter(prefix="/api")
settings = get_settings()
manager = JobManager(settings)
VOICE_TYPES = {
    "audio/webm": (".webm", "audio/webm"),
    "audio/mp4": (".mp4", "audio/mp4"),
    "audio/mpeg": (".mp3", "audio/mpeg"),
    "audio/ogg": (".ogg", "audio/ogg"),
    "audio/wav": (".wav", "audio/wav"),
    "audio/x-wav": (".wav", "audio/wav"),
}


def error(status: int, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail=message)


@router.get("/health")
def health():
    return {"status": "ok", "gemini": settings.gemini_enabled, "sample": True}


@router.post("/projects/sample", status_code=202)
async def create_sample():
    return await manager.create_sample()


@router.post("/projects", status_code=202)
async def create_project(
    files: list[UploadFile] = File(...),
    cast: str = Form(...),
    genre: Genre = Form(...),
    notes: str = Form(""),
    voice_note: UploadFile | None = File(None),
):
    if not settings.gemini_enabled:
        raise error(503, "GEMINI_API_KEY is required for your own media. Sample mode works without it.")
    cast_names = [name.strip() for name in cast.split(",") if name.strip()][:12]
    if not cast_names:
        raise error(422, "Add at least one cast member.")
    project_id = manager.new_id()
    directory = manager.project_dir(project_id)
    uploads = directory / "uploads"
    uploads.mkdir(parents=True, exist_ok=False)
    inputs: list[AssetInput] = []
    voice_path: Path | None = None
    try:
        validate_upload_count(len(files))
        for index, upload in enumerate(files, start=1):
            original_name = Path(upload.filename or "").name
            content = await upload.read(100 * 1024 * 1024 + 1)
            kind = validate_upload(original_name, upload.content_type or "", len(content))
            suffix = Path(original_name).suffix.lower() or (".mp4" if kind == "video" else ".jpg")
            destination = uploads / f"{index:02d}{suffix}"
            await asyncio.to_thread(destination.write_bytes, content)
            inputs.append(
                AssetInput(
                    filename=original_name,
                    content_type=upload.content_type or "",
                    path=destination,
                    size=len(content),
                )
            )
        if voice_note and voice_note.filename:
            content = await voice_note.read(20 * 1024 * 1024 + 1)
            if len(content) > 20 * 1024 * 1024:
                raise UploadValidationError("Voice note exceeds the 20 MB limit.")
            mime = (voice_note.content_type or "").split(";", 1)[0].lower()
            if mime not in VOICE_TYPES:
                raise UploadValidationError("Voice note must be WebM, MP4/AAC, MP3, OGG, or WAV audio.")
            suffix, _ = VOICE_TYPES[mime]
            voice_path = directory / f"voice{suffix}"
            await asyncio.to_thread(voice_path.write_bytes, content)
        return await manager.create(project_id, inputs, cast_names, genre, notes, voice_path)
    except UploadValidationError as exception:
        await asyncio.to_thread(shutil.rmtree, directory, True)
        raise error(422, str(exception)) from exception


@router.get("/projects/{project_id}")
def project(project_id: str):
    try:
        return manager.get(project_id).snapshot()
    except LookupError as exception:
        raise error(404, str(exception)) from exception


@router.get("/projects/{project_id}/events")
async def project_events(project_id: str, request: Request):
    try:
        job = manager.get(project_id)
    except LookupError as exception:
        raise error(404, str(exception)) from exception
    try:
        after_id = max(0, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        after_id = 0

    async def stream():
        async for event in job.events.stream(after_id):
            if await request.is_disconnected():
                return
            if event is None:
                yield ": projection booth heartbeat\n\n"
            else:
                yield f"id: {event.id}\ndata: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/projects/{project_id}/download")
def download(project_id: str):
    try:
        path = manager.press_kit_zip(project_id)
        return FileResponse(path, filename=f"cutline-{project_id}-press-kit.zip")
    except LookupError as exception:
        raise error(409, str(exception)) from exception
