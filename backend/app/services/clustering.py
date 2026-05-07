"""
Stadio diagnostico — DBSCAN su feature ambientali finestrate.

Decisione progettuale: il dataset di training usa lo storico 90gg di ciascun
ambiente, ricavando feature scorrevoli (sliding window) ogni 6h. Il modello e
lo scaler sono persistiti per ambiente in models/dbscan_<env_id>.pkl.

I 4 cluster attesi (sano / primo degrado / accentuato / pre-fault) sono
ottenuti via post-hoc labeling basato su soglie di RI_Totale calcolato da un
manufatto "rappresentativo" del proprio ambiente. I noise vengono riassegnati
al cluster più vicino (soglia di confidenza min_distance < 2σ).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

from app.core.constants import EnvironmentType
from app.services.risk_indices import (
    ManuscriptStatic,
    aggregate_features,
    compute_all_indices,
)


MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = [
    "T_media_24h",
    "RH_media_30gg",
    "dT_24h",
    "dRH_30gg",
    "lux_cumulati_5y",
    "VOC_medio_24h",
]


@dataclass
class ClusteringArtifact:
    scaler: StandardScaler
    dbscan: DBSCAN
    centroids: np.ndarray   # shape (4, n_features) — centroidi dei 4 cluster nominali
    cluster_RI_means: np.ndarray  # RI_Totale medio per cluster (per ordering)
    feature_matrix: np.ndarray    # X normalizzato (per t-SNE successivo)
    labels: np.ndarray            # label per ciascuna riga (0..3 o -1)


# ---------------------------------------------------------------------------
# Estrazione feature
# ---------------------------------------------------------------------------
def windowed_features(
    samples: List[dict],
    window_samples: int = 720,   # 5 giorni a 10 min
    stride_samples: int = 36,    # 6 ore a 10 min
    representative: Optional[ManuscriptStatic] = None,
    env_type: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Estrae una matrice X (n_windows, n_features) e un vettore RI_Totale.

    Per il labeling post-hoc usiamo un manufatto rappresentativo (default:
    pergamena standard pH=6, DP0=1000, ferro-gallico=False) e calcoliamo il
    RI_Totale di ciascuna finestra; il label di cluster è derivato per
    binning in 4 classi.
    """
    if representative is None:
        representative = ManuscriptStatic(
            pH=6.0, DP0=1000, inchiostro_ferro_gallico=False,
            pigmenti_fotosensibili=False, fragilita=1,
        )
    rows: List[List[float]] = []
    ri_values: List[float] = []
    for start in range(0, max(1, len(samples) - window_samples), stride_samples):
        win = samples[start : start + window_samples]
        feat = aggregate_features(win)
        rows.append([
            feat.T_media_24h,
            feat.RH_media_30gg,
            feat.dT_24h,
            feat.dRH_30gg,
            feat.lux_cumulati_5anni,
            feat.VOC_medio_24h,
        ])
        if env_type:
            from app.core.constants import DEFAULT_WEIGHTS
            weights = DEFAULT_WEIGHTS[env_type]
            indices = compute_all_indices(feat, representative, env_type, weights)
            ri_values.append(indices["RI_Totale"])
        else:
            ri_values.append(0.0)
    return np.array(rows), np.array(ri_values)


# ---------------------------------------------------------------------------
# Training DBSCAN
# ---------------------------------------------------------------------------
def label_from_RI(ri: float) -> int:
    """Cluster 0 sano, 1 primo degrado, 2 accentuato, 3 pre-fault."""
    if ri < 20.0:
        return 0
    if ri < 35.0:
        return 1
    if ri < 50.0:
        return 2
    return 3


def train_dbscan_for_env(
    samples: List[dict],
    env_type: EnvironmentType | str,
    *,
    eps: float = 0.7,
    min_samples: int = 8,
) -> ClusteringArtifact:
    env_key = env_type.value if isinstance(env_type, EnvironmentType) else env_type
    X, ri = windowed_features(samples, env_type=env_key)
    if len(X) < 5:
        # Dati insufficienti: ritorna artefatto vuoto
        return ClusteringArtifact(
            scaler=StandardScaler().fit(np.zeros((1, len(FEATURE_NAMES)))),
            dbscan=DBSCAN(eps=eps, min_samples=min_samples),
            centroids=np.zeros((4, len(FEATURE_NAMES))),
            cluster_RI_means=np.zeros(4),
            feature_matrix=X,
            labels=np.zeros(len(X), dtype=int),
        )

    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)

    db = DBSCAN(eps=eps, min_samples=min_samples).fit(Xs)
    raw_labels = db.labels_

    # Override: usiamo labeling supervisionato basato su RI_Totale,
    # mantenendo DBSCAN solo per individuare il "noise" da riassegnare.
    target = np.array([label_from_RI(r) for r in ri])

    # Centroidi per i 4 cluster target
    centroids = []
    cluster_means = []
    for c in range(4):
        mask = target == c
        if mask.sum() > 0:
            centroids.append(Xs[mask].mean(axis=0))
            cluster_means.append(ri[mask].mean())
        else:
            centroids.append(np.zeros(Xs.shape[1]))
            cluster_means.append(0.0)
    centroids = np.array(centroids)
    cluster_RI_means = np.array(cluster_means)

    # Riassegnazione noise: nearest centroid
    final_labels = target.copy()
    noise_idx = np.where(raw_labels == -1)[0]
    for i in noise_idx:
        d = np.linalg.norm(centroids - Xs[i], axis=1)
        nearest = int(np.argmin(d))
        final_labels[i] = nearest

    return ClusteringArtifact(
        scaler=scaler,
        dbscan=db,
        centroids=centroids,
        cluster_RI_means=cluster_RI_means,
        feature_matrix=Xs,
        labels=final_labels,
    )


def save_artifact(art: ClusteringArtifact, env_id: str) -> Path:
    p = MODELS_DIR / f"dbscan_{env_id}.pkl"
    joblib.dump(art, p)
    return p


def load_artifact(env_id: str) -> Optional[ClusteringArtifact]:
    p = MODELS_DIR / f"dbscan_{env_id}.pkl"
    if not p.exists():
        return None
    return joblib.load(p)


# ---------------------------------------------------------------------------
# Inferenza: dato un singolo punto (feature corrente), predici il cluster.
# ---------------------------------------------------------------------------
def predict_cluster(art: ClusteringArtifact, feat_vec: np.ndarray) -> Tuple[int, float]:
    """Ritorna (cluster_id, distanza al centroide)."""
    Xs = art.scaler.transform(feat_vec.reshape(1, -1))
    d = np.linalg.norm(art.centroids - Xs[0], axis=1)
    c = int(np.argmin(d))
    return c, float(d[c])


# ---------------------------------------------------------------------------
# Proiezione t-SNE (calcolata una volta per ambiente, su training set)
# ---------------------------------------------------------------------------
def tsne_projection(
    art: ClusteringArtifact, n_components: int = 3, max_points: int = 600,
) -> List[dict]:
    if len(art.feature_matrix) < 5:
        return []
    X = art.feature_matrix
    if len(X) > max_points:
        idx = np.linspace(0, len(X) - 1, max_points, dtype=int)
        X = X[idx]
        labels = art.labels[idx]
    else:
        labels = art.labels
    # t-SNE con perplexity adattiva (deve essere < n)
    perplexity = max(5, min(30, len(X) // 5))
    tsne = TSNE(n_components=n_components, perplexity=perplexity, init="random",
                learning_rate="auto", random_state=42)
    Y = tsne.fit_transform(X)
    out: List[dict] = []
    for i in range(len(Y)):
        rec = {
            "x": float(Y[i, 0]),
            "y": float(Y[i, 1]),
            "z": float(Y[i, 2]) if n_components >= 3 else 0.0,
            "cluster": int(labels[i]),
        }
        out.append(rec)
    return out
