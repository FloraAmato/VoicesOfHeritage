"""
WebSocket per stream live di telemetrie simulate.

In modalità demo (DEMO_TIME_COMPRESSION) ogni "tick" reale produce N campioni
simulati in modo da rendere percepibili gli scenari A–E nei pochi secondi
disponibili durante una presentazione.
"""

from __future__ import annotations

import asyncio
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.simulator import DEMO_TIME_COMPRESSION
from app.services.store import store


ws_router = APIRouter()
_clients: Set[WebSocket] = set()
_broadcast_lock = asyncio.Lock()


async def _broadcast(message: dict) -> None:
    async with _broadcast_lock:
        dead = []
        payload = json.dumps(message, default=str)
        for ws in list(_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _clients.discard(ws)


async def telemetry_loop(tick_seconds: float = 1.0, samples_per_tick: int = DEMO_TIME_COMPRESSION):
    """
    Loop infinito: ogni `tick_seconds` produce `samples_per_tick` campioni
    simulati per ciascun ambiente, li accumula nello store e li broadcasta.
    Avviato come background task in lifespan().
    """
    while True:
        try:
            for _ in range(max(1, samples_per_tick)):
                samples = store.simulators.step_all()
                for s in samples:
                    store.append_telemetry(s)
                await _broadcast({"type": "telemetry_batch", "samples": samples})
        except Exception as e:  # noqa: BLE001
            await _broadcast({"type": "error", "message": str(e)})
        await asyncio.sleep(tick_seconds)


@ws_router.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await websocket.accept()
    _clients.add(websocket)
    try:
        # Tieni la connessione aperta; ignoriamo i messaggi del client
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
