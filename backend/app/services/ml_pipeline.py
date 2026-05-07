"""
Orchestrazione pipeline ML: addestramento al boot, cache in memoria,
inferenza per manufatto.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from app.core.constants import EnvironmentType
from app.services.clustering import (
    ClusteringArtifact,
    load_artifact as load_dbscan,
    predict_cluster,
    save_artifact as save_dbscan,
    train_dbscan_for_env,
    tsne_projection,
)
from app.services.prognostic import (
    PrognosticArtifact,
    load_artifact as load_prog,
    predict_RUT,
    predict_trajectory,
    save_artifact as save_prog,
    train_for_env as train_prog,
)
from app.services.risk_indices import aggregate_features
from app.services.store import store


_dbscan_cache: Dict[str, ClusteringArtifact] = {}
_prog_cache: Dict[str, PrognosticArtifact] = {}
_tsne_cache: Dict[str, list] = {}


def train_or_load_all() -> None:
    """Carica modelli persistiti se presenti, altrimenti addestra e salva."""
    for env in store.environments.values():
        # DBSCAN
        art = load_dbscan(env.id)
        if art is None:
            samples = list(store.telemetry[env.id])
            art = train_dbscan_for_env(samples, env.tipo)
            save_dbscan(art, env.id)
        _dbscan_cache[env.id] = art
        # Prognostico
        prog = load_prog(env.id)
        if prog is None:
            samples = list(store.telemetry[env.id])
            prog = train_prog(samples, env.tipo)
            save_prog(prog, env.id)
        _prog_cache[env.id] = prog
        # t-SNE proiezione (cache)
        try:
            _tsne_cache[env.id] = tsne_projection(art)
        except Exception:
            _tsne_cache[env.id] = []


def get_cluster_for_manuscript(manuscript_id: str) -> int:
    """Ritorna il cluster diagnostico corrente del manufatto."""
    m = store.manuscripts[manuscript_id]
    art = _dbscan_cache.get(m.ambiente_id)
    if not art:
        return -1
    quota = m.posizione.quota.value if (
        store.environments[m.ambiente_id].tipo == EnvironmentType.SALA_STORICA
    ) else None
    series = store.get_telemetry(m.ambiente_id, limit=720, quota=quota)
    if not series:
        return -1
    feat = aggregate_features(series)
    vec = np.array([
        feat.T_media_24h, feat.RH_media_30gg, feat.dT_24h,
        feat.dRH_30gg, feat.lux_cumulati_5anni, feat.VOC_medio_24h,
    ])
    cluster, _ = predict_cluster(art, vec)
    return cluster


def predict_for_manuscript(manuscript_id: str) -> dict:
    """Calcola RUT-A, traiettoria e cluster per il manufatto."""
    from app.services.risk_pipeline import compute_indices_for_manuscript

    m = store.manuscripts[manuscript_id]
    art = _prog_cache.get(m.ambiente_id)
    indices = compute_indices_for_manuscript(manuscript_id)
    current_RI = indices["RI_Totale"]
    cluster = get_cluster_for_manuscript(manuscript_id)

    if art is None:
        return {
            "manuscript_id": manuscript_id,
            "current_RI": current_RI,
            "predicted_RI_30d": current_RI,
            "RUT_A_days": 9999.0,
            "RUT_A_lower": 9999.0,
            "RUT_A_upper": 9999.0,
            "trajectory": [],
            "cluster": cluster,
        }

    quota = m.posizione.quota.value if (
        store.environments[m.ambiente_id].tipo == EnvironmentType.SALA_STORICA
    ) else None
    series = store.get_telemetry(m.ambiente_id, limit=720, quota=quota)
    feat = aggregate_features(series)
    vec = np.array([
        feat.T_media_24h, feat.RH_media_30gg, feat.dT_24h,
        feat.dRH_30gg, feat.lux_cumulati_5anni, feat.VOC_medio_24h,
    ])
    rut, low, up = predict_RUT(art, vec)
    traj = predict_trajectory(art, current_RI, horizon_days=30)

    return {
        "manuscript_id": manuscript_id,
        "current_RI": current_RI,
        "predicted_RI_30d": traj[-1]["RI_pred"] if traj else current_RI,
        "RUT_A_days": rut,
        "RUT_A_lower": low,
        "RUT_A_upper": up,
        "trajectory": traj,
        "cluster": cluster,
    }


def get_tsne(env_id: str, current_manuscript_id: Optional[str] = None) -> dict:
    pts = _tsne_cache.get(env_id, [])
    out = {"points": pts}
    if current_manuscript_id and pts:
        cluster = get_cluster_for_manuscript(current_manuscript_id)
        # Punto rappresentativo: centroide del cluster nello spazio t-SNE
        cluster_pts = [p for p in pts if p["cluster"] == cluster]
        if cluster_pts:
            x = sum(p["x"] for p in cluster_pts) / len(cluster_pts)
            y = sum(p["y"] for p in cluster_pts) / len(cluster_pts)
            z = sum(p["z"] for p in cluster_pts) / len(cluster_pts)
            out["current"] = {"x": x, "y": y, "z": z, "cluster": cluster}
    return out
