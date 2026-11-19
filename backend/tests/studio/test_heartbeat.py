import pytest

from app.events import EventBus
from app.studio.graph import emit_heartbeat


@pytest.mark.asyncio
async def test_heartbeat_emits_during_slow_stage():
    bus = EventBus("heartbeat")
    async def work():
        import asyncio
        await asyncio.sleep(0.05)
        return 42
    result = await emit_heartbeat(bus, "researcher", "Researching", 10, work())
    assert result == 42
    assert bus.events[0].agent == "researcher"
    assert bus.events[0].status == "running"
