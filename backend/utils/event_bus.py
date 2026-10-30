"""
Quorum — Event Bus
Async pub/sub for broadcasting pipeline events to WebSocket subscribers.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

logger = logging.getLogger("quorum.eventbus")

# Max subscribers to prevent unbounded growth
_MAX_SUBSCRIBERS = 50


class EventBus:
    def __init__(self):
        self.subscribers: list[Callable[[dict], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[dict], Awaitable[None]]):
        if callback not in self.subscribers:
            if len(self.subscribers) >= _MAX_SUBSCRIBERS:
                logger.warning("EventBus: subscriber limit reached, ignoring new subscriber")
                return
            self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict], Awaitable[None]]):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    async def emit(self, event_type: str, analysis_id: str, data: dict):
        if not self.subscribers:
            return
        message = {
            "type": event_type,
            "analysis_id": analysis_id,
            "data": data,
        }
        tasks = [
            asyncio.create_task(self._safe_call(sub, message))
            for sub in self.subscribers
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call(self, callback, message):
        try:
            await callback(message)
        except Exception as e:
            logger.warning(f"EventBus subscriber error: {e}")


event_bus = EventBus()


async def emit_agent_log(
    analysis_id: str | None, agent: str, stage: str, message: str, details: str = ""
):
    """Emit an agent progress event for the live debate feed (no-op without an analysis ID)."""
    if not analysis_id:
        return
    await event_bus.emit("analysis_log", analysis_id, {
        "agent": agent,
        "stage": stage,
        "message": message,
        "details": (details or "")[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
