from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router, settings

app = FastAPI(title="CUTLINE", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range"],
)
app.include_router(router)
app.mount("/media", StaticFiles(directory=settings.data_dir), name="media")


@app.get("/")
def root():
    return {"name": "CUTLINE", "api": "/api/health"}
