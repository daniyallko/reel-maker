import asyncio
import time
from collections.abc import AsyncIterator

from app.schemas import AgentStatusEvent


class EventBus:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self._events: list[AgentStatusEvent] = []
        self._condition = asyncio.Condition()
        self._terminal = False

    @property
    def events(self) -> list[AgentStatusEvent]:
        return list(self._events)

    async def emit(
        self,
        agent: str,
        status: str,
        message: str,
        progress: float,
        **payload,
    ) -> AgentStatusEvent:
        assets = payload.pop("assets", None)
        event_payload = payload.pop("payload", None) or payload or None
        async with self._condition:
            event = AgentStatusEvent(
                id=len(self._events) + 1,
                project_id=self.project_id,
                agent=agent,
                status=status,
                message=message,
                progress=progress,
                timestamp=time.time(),
                assets=assets,
                payload=event_payload,
            )
            self._events.append(event)
            self._condition.notify_all()
        return event

    async def close(self) -> None:
        async with self._condition:
            self._terminal = True
            self._condition.notify_all()

    async def stream(self, after_id: int = 0) -> AsyncIterator[AgentStatusEvent | None]:
        cursor = after_id
        while True:
            async with self._condition:
                while cursor >= len(self._events) and not self._terminal:
                    try:
                        await asyncio.wait_for(self._condition.wait(), timeout=15)
                    except TimeoutError:
                        break
                if cursor < len(self._events):
                    batch = self._events[cursor:]
                    cursor = len(self._events)
                elif self._terminal:
                    return
                else:
                    batch = None
            if batch is None:
                yield None
            else:
                for event in batch:
                    yield event
