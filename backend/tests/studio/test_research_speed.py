import pytest

from app.studio.research import FirecrawlResearch, research_url


@pytest.mark.asyncio
async def test_research_timeout_returns_primary_source(monkeypatch):
    class SlowDDGS:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def text(self, *_args, **_kwargs):
            import time
            time.sleep(5)
            return []
    monkeypatch.setattr("app.studio.research.DDGS", SlowDDGS)
    sources = await research_url("https://acme.example", "Acme AI", timeout=0.01)
    assert sources[0].url == "https://acme.example"
    assert sources[0].claim == "Primary source supplied by the user"


@pytest.mark.asyncio
async def test_firecrawl_is_used_when_configured(monkeypatch):
    calls = []
    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {"data": [{"url": "https://acme.example/review", "title": "Acme review", "description": "Independent Acme review"}]}
    async def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    provider = FirecrawlResearch(post=fake_post)
    sources = await provider.research("https://acme.example", "Acme AI")
    assert calls
    assert sources[0].url == "https://acme.example/review"
