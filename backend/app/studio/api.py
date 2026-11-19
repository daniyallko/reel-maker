from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.studio.jobs import StudioJobManager
from app.studio.urls import sample_site_url

router = APIRouter(prefix="/api/studio")
manager = StudioJobManager(get_settings())


class StudioCreateRequest(BaseModel):
    url: str
    style: Literal["launch", "tech_launch", "deep_dive", "roast", "founder"] = "launch"
    voice: Literal["Charon", "Fenrir", "Puck", "Aoede"] = "Fenrir"


def error(status: int, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail=message)


@router.post("/projects", status_code=202)
async def create_project(input: StudioCreateRequest):
    try:
        return await manager.create(input.url, input.style, input.voice)
    except ValueError as exception:
        raise error(422, str(exception)) from exception


@router.post("/projects/sample", status_code=202)
async def create_sample():
    return await manager.create(sample_site_url(), "launch", "Fenrir", sample=True)


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
        return FileResponse(path, filename=f"link2reel-{project_id}.zip")
    except LookupError as exception:
        raise error(409, str(exception)) from exception
