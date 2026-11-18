import time
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance

from app.media.qa import verify_trailer

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8000"
INPUT_DIR = ROOT / "data" / "real-e2e-inputs"


def prepare_inputs() -> list[Path]:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = sorted((ROOT / "assets" / "sample" / "uploads").glob("*.jpg"))
    paths: list[Path] = []
    for index, source in enumerate(sources):
        destination = INPUT_DIR / f"frame-{index:02d}.jpg"
        destination.write_bytes(source.read_bytes())
        paths.append(destination)
    for index, source in enumerate(sources[:2], start=len(paths)):
        image = Image.open(source).convert("RGB")
        image = ImageEnhance.Contrast(image).enhance(1.12 + index * 0.03)
        image = image.crop((12, 12, image.width - 12, image.height - 12))
        destination = INPUT_DIR / f"frame-{index:02d}.jpg"
        image.save(destination, "JPEG", quality=88)
        paths.append(destination)
    return paths


def main():
    paths = prepare_inputs()
    with httpx.Client(timeout=120) as client:
        files = [("files", (path.name, path.read_bytes(), "image/jpeg")) for path in paths]
        voice = ROOT / "assets" / "sample" / "audio" / "voice-00.wav"
        if voice.exists():
            files.append(("voice_note", ("directors-note.wav", voice.read_bytes(), "audio/wav")))
        response = client.post(
            f"{BASE}/api/projects",
            files=files,
            data={
                "cast": "Maya,Theo,Nina,Jules",
                "genre": "comedy",
                "notes": "Nobody admits who booked the house. The wrong turn became the whole weekend.",
            },
        )
        response.raise_for_status()
        project = response.json()
        project_id = project["id"]
        print(f"Real Gemini project: {project_id}", flush=True)
        deadline = time.time() + 900
        last_status = None
        while time.time() < deadline:
            snapshot = client.get(f"{BASE}/api/projects/{project_id}").json()
            status = snapshot["status"]
            if status != last_status:
                print(f"Status: {status}", flush=True)
                last_status = status
            if status == "complete":
                output = snapshot["output"]
                assert 20 <= output["duration"] <= 25
                assert 1 <= len(output["edl"]["segments"]) <= 10
                assert len(output["cast_cards"]) == 4
                assert any(event["agent"] == "memory_curator" for event in snapshot["events"])
                assert any(event["agent"] == "screenwriter" for event in snapshot["events"])
                assert snapshot["events"][-1]["agent"] == "premiere"
                trailer = ROOT / "data" / project_id / "output" / "trailer.mp4"
                qa = verify_trailer(trailer)
                assert qa.valid, qa.errors
                poster = Image.open(ROOT / "data" / project_id / "output" / "poster.png")
                assert poster.size == (1080, 1920)
                archive = client.get(f"{BASE}/api/projects/{project_id}/download")
                assert archive.status_code == 200
                assert archive.content[:2] == b"PK"
                print({
                    "status": "passed",
                    "project_id": project_id,
                    "title": output["edl"]["title"],
                    "duration": qa.duration,
                    "shots": len(output["edl"]["segments"]),
                    "cast_cards": len(output["cast_cards"]),
                    "kept_assets": sum(asset["kept"] for asset in snapshot["assets"]),
                }, flush=True)
                return
            if status == "failed":
                raise RuntimeError(snapshot.get("error") or "Real pipeline failed")
            time.sleep(5)
        raise TimeoutError(f"Real pipeline did not finish within 15 minutes: {last_status}")


if __name__ == "__main__":
    main()
