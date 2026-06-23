"""In-memory log streaming for real-time SSE delivery."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

_history: deque[dict[str, Any]] = deque(maxlen=300)
_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()


def push(entry: dict[str, Any]) -> None:
    _history.append(entry)
    dead: set[asyncio.Queue[dict[str, Any]]] = set()
    for q in _subscribers:
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            dead.add(q)
    _subscribers.difference_update(dead)


def subscribe() -> asyncio.Queue[dict[str, Any]]:
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
