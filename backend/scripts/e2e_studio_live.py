import os
from pathlib import Path
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.studio.renderer import verify_studio_video
from app.studio.vision import REQUIRED_CRITERIA

BASE = "http://127.0.0.1:8000"


def main():
    topic = os.environ.get("STUDIO_TEST_TOPIC", "").strip()
    style = os.environ.get("STUDIO_STYLE", "tech_launch")
    quality_mode = os.environ.get("STUDIO_QUALITY_MODE", "strict")
    with httpx.Client(timeout=120) as client:
        if topic:
            response = client.post(
                f"{BASE}/api/studio/projects/inputs",
                files={
                    "source": (None, topic),
                    "style": (None, style),
                    "voice": (None, "Fenrir"),
                    "quality_mode": (None, quality_mode),
                },
            )
            expected_url = "inline://text"
        else:
            expected_url = os.environ.get("STUDIO_TEST_URL", "https://example.com")
            response = client.post(
                f"{BASE}/api/studio/projects",
                json={"url": expected_url, "style": style, "voice": "Fenrir", "quality_mode": quality_mode},
            )
        response.raise_for_status()
        project_id = response.json()["id"]
        print(f"LINK2REEL live project: {project_id}", flush=True)
        deadline = time.time() + 900
        while time.time() < deadline:
            snapshot = client.get(f"{BASE}/api/studio/projects/{project_id}").json()
            if snapshot["status"] == "complete":
                assert snapshot["source_url"] == expected_url, (snapshot["source_url"], expected_url)
                output = snapshot["output"]
                assert 30 <= output["duration"] <= 40
                minimum_scenes = 6 if topic else 4
                assert minimum_scenes <= len(output["scenes"]) <= 8, len(output["scenes"])
                assert output["sources"]
                assert all(scene["source_refs"] for scene in output["scenes"])
                if topic:
                    external_sources = [source for source in output["sources"] if source["url"].startswith(("http://", "https://"))]
                    assert external_sources, "Live topic smoke did not use external research"
                    script = output["script"].casefold()
                    for template_copy in ("behind the landing page", "the story behind the page", "the takeaway is simple"):
                        assert template_copy not in script, template_copy
                scores = output.get("critique_scores", {})
                if snapshot["quality_mode"] == "strict":
                    assert len(scores) == 6 and set(scores) == REQUIRED_CRITERIA, scores
                    assert min(scores.values()) >= 8, scores
                elif scores:
                    assert len(scores) == 6 and set(scores) == REQUIRED_CRITERIA, scores
                    assert min(scores.values()) >= 7, scores
                else:
                    assert output.get("review_label") == "Unreviewed draft"
                project_dir = Path(__file__).resolve().parents[1] / "data" / project_id
                contact = project_dir / "audit" / "contact-sheet.png"
                assert contact.exists()
                qa = verify_studio_video(project_dir / "output" / "trailer.mp4")
                assert qa.valid, qa.errors
                archive = client.get(f"{BASE}/api/studio/projects/{project_id}/download")
                assert archive.status_code == 200
                assert archive.content[:2] == b"PK"
                print({
                    "status": "passed",
                    "project_id": project_id,
                    "source_url": snapshot["source_url"],
                    "title": output["title"],
                    "duration": output["duration"],
                    "scenes": len(output["scenes"]),
                    "sources": len(output["sources"]),
                    "external_research": bool(topic),
                    "critique_scores": scores,
                    "review_label": output.get("review_label"),
                }, flush=True)
                return
            if snapshot["status"] == "failed":
                raise RuntimeError(snapshot.get("error") or "Studio production failed")
            time.sleep(5)
        raise TimeoutError("Studio production exceeded 15 minutes")


if __name__ == "__main__":
    main()
