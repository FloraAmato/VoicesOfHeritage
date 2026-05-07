"""
Orchestrazione: dato un manuscript_id, calcola RI usando lo storico di
telemetria del proprio ambiente e i pesi runtime correnti.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from app.core.constants import EnvironmentType
from app.models.schemas import Manuscript
from app.services.risk_indices import (
    ManuscriptStatic,
    aggregate_features,
    compute_all_indices,
)
from app.services.store import store


def manuscript_to_static(m: Manuscript) -> ManuscriptStatic:
    return ManuscriptStatic(
        pH=m.pH_stimato,
        DP0=m.DP0_stimato,
        inchiostro_ferro_gallico=m.inchiostro_ferro_gallico,
        pigmenti_fotosensibili=m.pigmenti_fotosensibili,
        fragilita=m.fragilita_osservata,
    )


def compute_indices_for_manuscript(
    manuscript_id: str,
    *,
    weights_override: Optional[Dict[str, float]] = None,
    window_samples: int = 4320,  # 30 giorni × 144 campioni/giorno
) -> dict:
    """
    Calcola gli indici correnti per un manufatto.

    Per la sala storica con doppia traccia, scegliamo la quota in cui il
    manufatto è effettivamente collocato (manuscript.posizione.quota).
    """
    m = store.manuscripts[manuscript_id]
    env = store.environments[m.ambiente_id]

    quota_filter = None
    if env.tipo == EnvironmentType.SALA_STORICA:
        quota_filter = m.posizione.quota.value

    series = store.get_telemetry(env.id, limit=window_samples, quota=quota_filter)

    # Banda EN15757 storicizzata: ricavata dalla finestra stessa (10°/90° pct)
    # Decisione: per semplicità usiamo media ± 1.5 std come banda di riferimento
    if series:
        import numpy as np
        T = np.array([s["T"] for s in series])
        RH = np.array([s["RH"] for s in series])
        band_T = (float(T.mean() - 1.5 * T.std()), float(T.mean() + 1.5 * T.std()))
        band_RH = (float(RH.mean() - 1.5 * RH.std()), float(RH.mean() + 1.5 * RH.std()))
    else:
        band_T = (16.0, 22.0)
        band_RH = (45.0, 60.0)

    features = aggregate_features(series, fragilita_band_T=band_T, fragilita_band_RH=band_RH)

    weights = weights_override or store.get_weights(env.tipo.value)
    indices = compute_all_indices(features, manuscript_to_static(m), env.tipo, weights)
    indices["manuscript_id"] = manuscript_id
    indices["timestamp"] = (
        series[-1]["timestamp"] if series else datetime.now(timezone.utc).isoformat()
    )
    return indices
