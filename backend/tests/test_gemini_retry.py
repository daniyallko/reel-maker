from types import SimpleNamespace

import pytest

from app.providers.gemini import GEMINI_MODEL, GEMINI_MODELS, GeminiProvider


@pytest.mark.asyncio
async def test_gemini_retries_transient_unavailable(monkeypatch):
    calls = []
    response = SimpleNamespace(parsed={"ok": True})
    def generate_content(**kwargs):
        calls.append(kwargs)
        if len(calls) < 3:
            raise RuntimeError("503 UNAVAILABLE")
        return response
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    async def no_sleep(_):
        return None
    monkeypatch.setattr("app.providers.gemini.asyncio.sleep", no_sleep)
    result = await GeminiProvider("key")._generate(client, object(), ["test"])
    assert result is response
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_gemini_falls_back_to_available_model(monkeypatch):
    calls = []
    response = SimpleNamespace(parsed={"ok": True})
    def generate_content(**kwargs):
        calls.append(kwargs["model"])
        if kwargs["model"] == GEMINI_MODEL:
            raise RuntimeError("503 UNAVAILABLE")
        return response
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    async def no_sleep(_):
        return None
    monkeypatch.setattr("app.providers.gemini.asyncio.sleep", no_sleep)
    result = await GeminiProvider("key")._generate(client, object(), ["test"])
    assert result is response
    assert calls == [GEMINI_MODEL, GEMINI_MODEL, GEMINI_MODEL, GEMINI_MODELS[1]]


@pytest.mark.asyncio
async def test_gemini_times_out_hung_request(monkeypatch):
    import time
    calls = []
    def generate_content(**kwargs):
        calls.append(kwargs)
        time.sleep(1)
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    async def no_sleep(_):
        return None
    monkeypatch.setattr("app.providers.gemini.asyncio.sleep", no_sleep)
    with pytest.raises(TimeoutError):
        await GeminiProvider("key")._generate(client, object(), ["test"], timeout=0.01)
    assert calls
