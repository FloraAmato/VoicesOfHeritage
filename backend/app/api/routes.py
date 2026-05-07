"""
REST API VoH.

Endpoint principali:
  GET  /api/manuscripts                       — lista manoscritti
  GET  /api/manuscripts/{id}                  — dettaglio
  GET  /api/manuscripts/{id}/indices          — indici correnti
  GET  /api/manuscripts/{id}/indices/history  — serie storica RI
  POST /api/manuscripts/{id}/whatif           — calcolo indici con override

  GET  /api/environments                      — lista ambienti
  GET  /api/environments/{id}                 — dettaglio
  GET  /api/environments/{id}/telemetry       — telemetrie storiche

  GET  /api/weights/{env_type}                — pesi correnti
  PUT  /api/weights/{env_type}                — override pesi
  POST /api/weights/{env_type}/reset          — reset ai default
  GET  /api/thresholds                        — soglie ambientali (Tab.1)

  GET  /api/alerts                            — lista alert
  POST /api/alerts/{id}/ack                   — acknowledge

  POST /api/demo/scenario                     — trigger scenario A–E
  POST /api/demo/reset                        — reset scenari
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from app.core.constants import (
    DEFAULT_WEIGHTS,
    RI_THRESHOLDS,
    THRESHOLDS,
    WEIGHT_VARIABLES,
    EnvironmentType,
)
from app.models.schemas import (
    Alert,
    AlertStatus,
    Environment,
    Manuscript,
)
from app.services.alerts import get_recommendations as build_recommendations
from app.services.ml_pipeline import get_tsne, predict_for_manuscript
from app.services.risk_pipeline import compute_indices_for_manuscript
from app.services.simulator import Scenario
from app.services.store import store


router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Manuscripts
# ---------------------------------------------------------------------------
@router.get("/manuscripts", response_model=List[Manuscript])
def list_manuscripts():
    return list(store.manuscripts.values())


@router.get("/manuscripts/{manuscript_id}", response_model=Manuscript)
def get_manuscript(manuscript_id: str):
    m = store.manuscripts.get(manuscript_id)
    if not m:
        raise HTTPException(404, "Manuscript not found")
    return m


@router.get("/manuscripts/{manuscript_id}/indices")
def get_manuscript_indices(manuscript_id: str):
    if manuscript_id not in store.manuscripts:
        raise HTTPException(404, "Manuscript not found")
    return compute_indices_for_manuscript(manuscript_id)


@router.get("/manuscripts/{manuscript_id}/indices/history")
def get_indices_history(manuscript_id: str, limit: int = Query(200, ge=1, le=2000)):
    if manuscript_id not in store.manuscripts:
        raise HTTPException(404, "Manuscript not found")
    return store.get_indices_history(manuscript_id, limit=limit)


@router.get("/manuscripts/{manuscript_id}/predict")
def predict_endpoint(manuscript_id: str):
    if manuscript_id not in store.manuscripts:
        raise HTTPException(404, "Manuscript not found")
    return predict_for_manuscript(manuscript_id)


@router.get("/environments/{env_id}/tsne")
def env_tsne(env_id: str, manuscript_id: Optional[str] = None):
    if env_id not in store.environments:
        raise HTTPException(404, "Environment not found")
    return get_tsne(env_id, manuscript_id)


@router.get("/alerts/{alert_id}/recommendations")
def alert_recommendations(alert_id: str):
    a = next((x for x in store.alerts if x.id == alert_id), None)
    if not a:
        raise HTTPException(404, "Alert not found")
    return build_recommendations(a)


class WhatIfRequest(BaseModel):
    """Richiesta what-if: override telemetria target o pesi."""

    # Se forniti, usa questi valori per ricostruire feature sintetiche
    T_set: Optional[float] = None
    RH_set: Optional[float] = None
    lux_set: Optional[float] = None
    VOC_set: Optional[float] = None
    # Override pesi runtime
    weights_override: Optional[Dict[str, float]] = None
    # Cambio ipotetico di ambiente (per simulare riposizionamento)
    target_environment_id: Optional[str] = None


@router.post("/manuscripts/{manuscript_id}/whatif")
def manuscript_whatif(manuscript_id: str, req: WhatIfRequest = Body(...)):
    """
    Simula uno scenario alternativo per il manufatto SENZA salvare niente.
    Se cambia target_environment_id, usa la matrice pesi del nuovo ambiente.
    """
    if manuscript_id not in store.manuscripts:
        raise HTTPException(404, "Manuscript not found")
    m = store.manuscripts[manuscript_id]

    # Se cambia ambiente, applichiamo i pesi del nuovo ambiente
    if req.target_environment_id:
        target_env = store.environments.get(req.target_environment_id)
        if not target_env:
            raise HTTPException(404, "Target environment not found")
        weights = store.get_weights(target_env.tipo.value)
    else:
        weights = store.get_weights(store.environments[m.ambiente_id].tipo.value)

    if req.weights_override:
        weights = {**weights, **req.weights_override}

    # Override telemetria: ricostruiamo una serie sintetica usando il setpoint
    series = store.get_telemetry(m.ambiente_id, limit=4320)
    if any(v is not None for v in (req.T_set, req.RH_set, req.lux_set, req.VOC_set)):
        for s in series:
            s = dict(s)  # don't mutate ring
            if req.T_set is not None:
                s["T"] = req.T_set
            if req.RH_set is not None:
                s["RH"] = req.RH_set
            if req.lux_set is not None:
                s["lux"] = req.lux_set
            if req.VOC_set is not None:
                s["VOC"] = req.VOC_set

    return compute_indices_for_manuscript(
        manuscript_id, weights_override=weights
    )


# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------
@router.get("/environments", response_model=List[Environment])
def list_environments():
    return list(store.environments.values())


@router.get("/environments/{env_id}", response_model=Environment)
def get_environment(env_id: str):
    e = store.environments.get(env_id)
    if not e:
        raise HTTPException(404, "Environment not found")
    return e


@router.get("/environments/{env_id}/telemetry")
def get_telemetry(
    env_id: str,
    limit: int = Query(2000, ge=1, le=20000),
    quota: Optional[str] = Query(None, pattern="^(piano_terra|soppalco)$"),
    since_iso: Optional[str] = None,
):
    if env_id not in store.environments:
        raise HTTPException(404, "Environment not found")
    since = None
    if since_iso:
        try:
            since = datetime.fromisoformat(since_iso)
        except ValueError:
            raise HTTPException(400, "Invalid since_iso (expected ISO 8601)")
    return store.get_telemetry(env_id, limit=limit, since=since, quota=quota)


# ---------------------------------------------------------------------------
# Weights (Tab.3 — modificabili a runtime)
# ---------------------------------------------------------------------------
@router.get("/weights")
def get_all_weights():
    return {env: store.get_weights(env) for env in DEFAULT_WEIGHTS.keys()}


@router.get("/weights/{env_type}")
def get_weights(env_type: str):
    if env_type not in DEFAULT_WEIGHTS:
        raise HTTPException(404, "Unknown environment type")
    return {
        "environment_type": env_type,
        "weights": store.get_weights(env_type),
        "variables": list(WEIGHT_VARIABLES),
    }


@router.put("/weights/{env_type}")
def put_weights(env_type: str, weights: Dict[str, float] = Body(...)):
    if env_type not in DEFAULT_WEIGHTS:
        raise HTTPException(404, "Unknown environment type")
    unknown = set(weights.keys()) - set(WEIGHT_VARIABLES)
    if unknown:
        raise HTTPException(400, f"Unknown variables: {sorted(unknown)}")
    for k, v in weights.items():
        if not 0.0 <= float(v) <= 1.0:
            raise HTTPException(400, f"Weight {k} out of [0,1]: {v}")
    return store.set_weights(env_type, weights)


@router.post("/weights/{env_type}/reset")
def reset_weights(env_type: str):
    if env_type not in DEFAULT_WEIGHTS:
        raise HTTPException(404, "Unknown environment type")
    store.reset_weights(env_type)
    return store.get_weights(env_type)


# ---------------------------------------------------------------------------
# Thresholds (Tab.1 — sola lettura)
# ---------------------------------------------------------------------------
@router.get("/thresholds")
def get_thresholds():
    return {
        "environmental": THRESHOLDS,
        "risk_indices": RI_THRESHOLDS,
    }


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
@router.get("/alerts", response_model=List[Alert])
def list_alerts(status: Optional[AlertStatus] = None):
    alerts = store.list_alerts()
    if status:
        alerts = [a for a in alerts if a.status == status]
    return sorted(alerts, key=lambda a: a.timestamp, reverse=True)


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    note: Optional[str] = None


@router.post("/alerts/{alert_id}/ack")
def ack_alert(alert_id: str, update: AlertUpdate = Body(default=AlertUpdate())):
    fields = update.model_dump(exclude_none=True)
    if "status" not in fields:
        fields["status"] = AlertStatus.PRESO_IN_CARICO
    a = store.update_alert(alert_id, **fields)
    if not a:
        raise HTTPException(404, "Alert not found")
    return a


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------
class ScenarioTrigger(BaseModel):
    environment_id: str
    scenario: Scenario
    duration_hours: float = 72.0


@router.post("/demo/scenario")
def trigger_scenario(req: ScenarioTrigger):
    if req.environment_id not in store.environments:
        raise HTTPException(404, "Environment not found")
    store.simulators.trigger(req.environment_id, req.scenario, req.duration_hours)
    return {"status": "ok", "scenario": req.scenario, "environment_id": req.environment_id}


@router.post("/demo/reset")
def reset_scenarios():
    store.simulators.reset_all()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Aggregates (per Vista Collezione)
# ---------------------------------------------------------------------------
@router.get("/dashboard/summary")
def dashboard_summary():
    """KPI aggregati per la Vista Collezione."""
    total = len(store.manuscripts)
    crit = 0
    att = 0
    per_manuscript = []
    for m in store.manuscripts.values():
        idx = compute_indices_for_manuscript(m.id)
        per_manuscript.append({
            "manuscript_id": m.id,
            "nome": m.nome,
            "ambiente_id": m.ambiente_id,
            "RI_Totale": idx["RI_Totale"],
            "severity": idx["severity"],
        })
        if idx["severity"] == "critico":
            crit += 1
        elif idx["severity"] == "attenzione":
            att += 1
    open_alerts = sum(1 for a in store.alerts if a.status == AlertStatus.APERTO)
    return {
        "total": total,
        "critico": crit,
        "attenzione": att,
        "alerts_open": open_alerts,
        "manuscripts": per_manuscript,
    }
