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


# ---------------------------------------------------------------------------
# Loop di valutazione indici di rischio + emissione alert
# ---------------------------------------------------------------------------
async def indices_alert_loop(tick_seconds: float = 5.0):
    """
    Ogni `tick_seconds`:
      - calcola RI per ogni manufatto
      - storicizza l'osservazione
      - decide se emettere un nuovo alert (deduplica per manuscript+severity
        nelle ultime 5 minuti)
    """
    from datetime import datetime, timedelta, timezone

    from app.services.alerts import (
        compute_severity,
        detect_trigger,
        emit_alert,
    )
    from app.services.ml_pipeline import get_cluster_for_manuscript, predict_for_manuscript
    from app.services.risk_pipeline import compute_indices_for_manuscript

    last_emitted: dict[tuple[str, str], datetime] = {}

    while True:
        try:
            for m_id, m in list(store.simulators.simulators.items()):
                pass  # placeholder per espansioni
            for m_id in list(store.manuscripts.keys()):
                idx = compute_indices_for_manuscript(m_id)
                store.append_indices(m_id, idx)

                # Decide severity
                cluster = get_cluster_for_manuscript(m_id)
                rut = predict_for_manuscript(m_id).get("RUT_A_days", 9999.0)
                # Persistenza in attenzione: ultima ora di indici sopra 35
                hist = store.get_indices_history(m_id, limit=12)
                persistent = sum(1 for h in hist if h.get("RI_Totale", 0) >= 35.0) >= 8
                sev = compute_severity(idx, persistent_attention=persistent,
                                       cluster=cluster, rut_a=rut)
                if sev is None:
                    continue
                # Deduplica: stessa coppia (manuscript, severity) non più di 1 ogni 5 min
                key = (m_id, sev.value)
                now = datetime.now(timezone.utc)
                if key in last_emitted and (now - last_emitted[key]) < timedelta(minutes=5):
                    continue
                last_emitted[key] = now

                # Trigger
                last_sample = (
                    list(store.telemetry[store.manuscripts[m_id].ambiente_id])[-1]
                    if store.telemetry[store.manuscripts[m_id].ambiente_id] else None
                )
                tvar, tval, tmsg = detect_trigger(store.manuscripts[m_id], idx, last_sample)
                # Messaggi standard per scenario
                msg_map = {
                    "MEDIA": f"{tmsg}. Verifica condizioni e ispezione visiva entro 72h.",
                    "ALTA": f"{tmsg}. Intervento HVAC immediato. Considerare riposizionamento.",
                    "CRITICA": f"{tmsg}. Notifica al responsabile conservazione, sopralluogo entro 24h.",
                    "INFO": f"{tmsg}. Monitoraggio continuativo.",
                }
                emit_alert(m_id, sev, idx, tvar, tval, msg_map[sev.value])
                await _broadcast({"type": "alert_emitted", "manuscript_id": m_id, "severity": sev.value})
        except Exception as e:  # noqa: BLE001
            await _broadcast({"type": "error", "message": f"indices_loop: {e}"})
        await asyncio.sleep(tick_seconds)
