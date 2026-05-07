"""
FastAPI entry point per il backend VoH.

Avvio (locale):
    uvicorn app.main:app --reload --port 8000

Avvio (Docker): vedi root docker-compose.yml.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.websocket import indices_alert_loop, telemetry_loop, ws_router
from app.services.alerts import reload_rules
from app.services.ml_pipeline import train_or_load_all
from app.services.store import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap: genera storici, popola store, addestra modelli
    store.initialize(generate_history_days=90)
    reload_rules()
    train_or_load_all()

    # Background tasks: streaming live + valutazione periodica indici/alert
    task1 = asyncio.create_task(telemetry_loop(tick_seconds=1.0, samples_per_tick=10))
    task2 = asyncio.create_task(indices_alert_loop(tick_seconds=5.0))
    try:
        yield
    finally:
        for t in (task1, task2):
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="VoH — Voices of Heritage",
    description=(
        "Backend per il prototipo di dashboard di conservazione preventiva "
        "manoscritti antichi (CeRICT — Conservatorio di Benevento). "
        "Architettura predittiva derivata da EFAISTOS (Test Before Invest, "
        "Polo P.R.I.D.E.), sensore artunified multiparametrico."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "voh-backend"}


@app.get("/")
def root():
    return {
        "service": "VoH — Voices of Heritage backend",
        "docs": "/docs",
        "health": "/health",
        "api": "/api",
        "websocket": "/ws/telemetry",
    }
