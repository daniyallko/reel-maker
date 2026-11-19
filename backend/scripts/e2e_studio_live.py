import time
import os

import httpx

from app.studio.renderer import verify_studio_video

BASE = "http://127.0.0.1:8000"


def main():
    with httpx.Client(timeout=120) as client:
        response = client.post(f"{BASE}/api/studio/projects", json={"url": os.environ.get("STUDIO_TEST_URL", "https://example.com"), "style": os.environ.get("STUDIO_STYLE", "tech_launch"), "voice": "Fenrir"})
        response.raise_for_status()
        expected_url = os.environ.get("STUDIO_TEST_URL", "https://example.com")
        project_id = response.json()["id"]
        print(f"LINK2REEL live project: {project_id}", flush=True)
        deadline = time.time() + 900
        while time.time() < deadline:
            snapshot = client.get(f"{BASE}/api/studio/projects/{project_id}").json()
            if snapshot["status"] == "complete":
                assert snapshot["source_url"] == expected_url, (snapshot["source_url"], expected_url)
                output = snapshot["output"]
                assert 30 <= output["duration"] <= 40
                assert len(output["scenes"]) == 4
                assert output["sources"]
                scores = output.get("critique_scores", {})
                assert scores and min(scores.values()) >= 8, scores
                contact = __import__("pathlib").Path(__file__).resolve().parents[1] / "data" / project_id / "audit" / "contact-sheet.png"
                assert contact.exists()
                trailer = snapshot["id"]
                qa = verify_studio_video(__import__("pathlib").Path(__file__).resolve().parents[1] / "data" / project_id / "output" / "trailer.mp4")
                assert qa.valid, qa.errors
                archive = client.get(f"{BASE}/api/studio/projects/{project_id}/download")
                assert archive.status_code == 200
                assert archive.content[:2] == b"PK"
                print({"status": "passed", "project_id": project_id, "source_url": snapshot["source_url"], "title": output["title"], "duration": output["duration"], "sources": len(output["sources"]), "critique_scores": scores}, flush=True)
                return
            if snapshot["status"] == "failed":
                raise RuntimeError(snapshot.get("error") or "Studio production failed")
            time.sleep(5)
        raise TimeoutError("Studio production exceeded 15 minutes")


if __name__ == "__main__":
    main()
