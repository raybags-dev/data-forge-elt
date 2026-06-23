"""In-memory log streaming for real-time SSE delivery."""

from __future__ import annotations

import asyncio
import contextlib
from collections import deque
from typing import Any

_history: deque[dict[str, Any]] = deque(maxlen=300)
_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_loop: asyncio.AbstractEventLoop | None = None


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Register the running event loop so push() works from any thread."""
    global _loop
    _loop = loop


def _put_safe(q: asyncio.Queue[dict[str, Any]], entry: dict[str, Any]) -> None:
    with contextlib.suppress(asyncio.QueueFull):
        q.put_nowait(entry)


def push(entry: dict[str, Any]) -> None:
    _history.append(entry)
    if not _subscribers:
        return
    loop = _loop
    if loop is not None and loop.is_running():
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for q in list(_subscribers):
            try:
                loop.call_soon_threadsafe(_put_safe, q, entry)
            except RuntimeError:
                dead.append(q)
        for q in dead:
            _subscribers.discard(q)
    else:
        # No event loop yet (startup) — best-effort direct put
        dead_sync: list[asyncio.Queue[dict[str, Any]]] = []
        for q in list(_subscribers):
            try:
                q.put_nowait(entry)
            except (asyncio.QueueFull, RuntimeError):
                dead_sync.append(q)
        for q in dead_sync:
            _subscribers.discard(q)


def subscribe() -> asyncio.Queue[dict[str, Any]]:
    global _loop
    with contextlib.suppress(RuntimeError):
        _loop = asyncio.get_running_loop()
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=300)
    _subscribers.add(q)
    for entry in _history:
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            break
    return q


def unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    _subscribers.discard(q)
