"""
Motore degli indici di rischio (D4.2.2.2 — cap. 6).

Implementa i 5 indici elementari + RI_Totale:
  - RI_Chimico        : invertito da TWEL = DP0 * f(pH)
  - RI_Meccanico      : frazione fuori dai limiti EN 15757 storicizzati
  - RI_Insetti        : polinomio di Brimblecombe (uova/anno) normalizzato
  - RI_Muffa          : ore/anno sopra LIM Sedlbauer
  - RI_Fotodeterioramento : ΔE* atteso a 5 anni di esposizione cumulata

Il RI_Totale combina i primi 4 con i coefficienti standard Michalski–Verticchio
(cfr. RI_TOTAL_COEFS). Il RI_Fotodeterioramento è esposto separatamente perché
la sua scala (ΔE*) non è un %.

Convenzione: tutti gli RI elementari sono espressi in % (0–100), tranne
RI_Meccanico che è in % di "ore-anno fuori EN15757" (tipicamente 0–10).
I pesi della matrice ambiente-dipendente (constants.DEFAULT_WEIGHTS) modulano
i contributi delle variabili d'ingresso al singolo RI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np

from app.core.constants import (
    DEFAULT_WEIGHTS,
    RI_THRESHOLDS,
    RI_TOTAL_COEFS,
    EnvironmentType,
)


# ---------------------------------------------------------------------------
# Input aggregato per il calcolo degli indici (feature finestrate del manufatto)
# ---------------------------------------------------------------------------
@dataclass
class RiskFeatures:
    # Parametri ambientali aggregati sulla finestra di osservazione
    T_media_24h: float          # °C
    T_media_30gg: float         # °C
    RH_media_24h: float         # %
    RH_media_30gg: float        # %
    dT_24h: float               # °C, max - min nelle ultime 24h
    dRH_24h: float              # %
    dRH_30gg: float             # %, ampiezza nella finestra
    lux_medio: float            # lux, media oraria nelle ore di "esposizione"
    lux_cumulati_5anni: float   # lux·h cumulativi proiettati a 5 anni
    VOC_medio_24h: float        # ppb
    PM10_medio_24h: float       # µg/m³
    gradiente_verticale_T: float  # °C tra P.T. e soppalco
    ore_sopra_LIM_anno: float   # ore/anno con RH > LIM Sedlbauer(T)
    frazione_fuori_EN15757: float  # frazione [0,1] del periodo fuori dalla banda storica


@dataclass
class ManuscriptStatic:
    """Caratterizzazione codicologica statica usata dagli indici di rischio."""

    pH: float
    DP0: int
    inchiostro_ferro_gallico: bool
    pigmenti_fotosensibili: bool
    fragilita: int  # 0..3


# ---------------------------------------------------------------------------
# Helper di clipping in [0, 100]
# ---------------------------------------------------------------------------
def _clip100(x: float) -> float:
    return max(0.0, min(100.0, float(x)))


# ---------------------------------------------------------------------------
# RI_Chimico  —  inversione di TWEL = DP0 * f(pH)
# ---------------------------------------------------------------------------
def f_pH(pH: float) -> float:
    """
    Fattore correttivo del pH sull'energia di attivazione.
    Lineare da 0.55 a pH=5 a 0.72 a pH=7 (D4.2.2.2 §6.1).
    Estrapolazione lineare oltre i bordi mantenendo continuità.
    """
    return 0.55 + (0.72 - 0.55) * (pH - 5.0) / (7.0 - 5.0)


def ri_chimico(features: RiskFeatures, ms: ManuscriptStatic, weights: Dict[str, float]) -> float:
    """
    RI_Chimico in %.

    Modello semplificato: il rischio chimico cresce con la temperatura media
    di lungo periodo (Arrhenius), con la presenza di inchiostro ferro-gallico
    e con bassi pH/DP0. Si usa la peso w[T_media_24h] per modulare la
    sensibilità termica e w[PM_VOC] per modulare l'effetto di PM/VOC catalitici.
    """
    # Componente Arrhenius normalizzata su un riferimento di 20°C (+10°C → ×2)
    T_eq = features.T_media_30gg
    arrhenius = 2 ** ((T_eq - 20.0) / 10.0)

    # Vulnerabilità intrinseca da pH e DP0
    f = f_pH(ms.pH)
    base_chem = 100.0 * (1.0 - f)  # pH basso → vicino a 45%
    dp0_factor = max(0.4, min(1.6, 800.0 / max(50.0, ms.DP0)))  # DP0 basso → factor>1

    # Inchiostro ferro-gallico catalizza l'idrolisi
    iron_gall = 1.25 if ms.inchiostro_ferro_gallico else 1.0

    # PM e VOC accelerano il degrado chimico
    voc_term = (features.VOC_medio_24h / 1000.0) * weights.get("PM_VOC", 0.5)
    pm_term = (features.PM10_medio_24h / 75.0) * weights.get("PM_VOC", 0.5)

    raw = (
        base_chem
        * arrhenius
        * dp0_factor
        * iron_gall
        * (1.0 + 0.3 * weights.get("T_media_24h", 0.5) * (arrhenius - 1.0))
        * (1.0 + 0.2 * (voc_term + pm_term))
    )
    return _clip100(raw)


# ---------------------------------------------------------------------------
# RI_Meccanico  —  frazione di tempo fuori EN 15757 storicizzato
# ---------------------------------------------------------------------------
def ri_meccanico(features: RiskFeatures, ms: ManuscriptStatic, weights: Dict[str, float]) -> float:
    """
    RI_Meccanico in % (annua di tempo fuori dalla banda EN 15757).

    Tipicamente 0–10%. La fragilità osservata e le oscillazioni rapide aumentano
    il valore. I pesi w[dT_24h] e w[dRH_24h] modulano la sensibilità alle
    oscillazioni rapide.
    """
    base = features.frazione_fuori_EN15757 * 100.0  # 0..100
    # Le fluttuazioni rapide pesano in modo non lineare
    fluct = (
        (features.dT_24h / 4.0) * weights.get("dT_24h", 0.5)
        + (features.dRH_24h / 12.0) * weights.get("dRH_24h", 0.5)
    )
    fragilita_factor = 1.0 + 0.25 * ms.fragilita
    raw = base * fragilita_factor * (1.0 + 0.5 * fluct)
    # In genere RI_Meccanico è 0–10% nel range realistico — clamp a 100 per safety
    return _clip100(raw)


# ---------------------------------------------------------------------------
# RI_Insetti  —  polinomio di Brimblecombe normalizzato a 1560 uova/anno @ 29°C
# ---------------------------------------------------------------------------
def brimblecombe_eggs_per_year(T: float, RH: float) -> float:
    """
    Approssimazione polinomiale del numero atteso di uova/anno per lepismatidi
    (Brimblecombe & Lankester). Massimo ~1560 a 29°C e RH 70%.
    Forma: prodotto di due gaussiane su T e RH.
    """
    if RH <= 50.0:
        return 0.0
    eggs_T = 1560.0 * math.exp(-((T - 29.0) ** 2) / (2 * 4.0**2))
    eggs_RH = math.exp(-((RH - 70.0) ** 2) / (2 * 10.0**2))
    return eggs_T * eggs_RH


def ri_insetti(features: RiskFeatures, ms: ManuscriptStatic, weights: Dict[str, float]) -> float:
    """RI_Insetti in % (proporzionale a uova/anno, saturato a 1560)."""
    eggs = brimblecombe_eggs_per_year(features.T_media_30gg, features.RH_media_30gg)
    raw = 100.0 * eggs / 1560.0
    # Modulazione ambientale
    env_mod = 1.0 + 0.3 * (weights.get("rischio_insetti", 0.5) - 0.5)
    return _clip100(raw * env_mod)


# ---------------------------------------------------------------------------
# RI_Muffa  —  ore/anno sopra LIM di Sedlbauer
# ---------------------------------------------------------------------------
def sedlbauer_LIM(T: float) -> float:
    """
    Limite inferiore di germinazione (LIM) di Sedlbauer.
    A 20°C il LIM è 75% RH; cala con T crescente.
    Approssimazione lineare nel range 5–35°C.
    """
    if T <= 5.0:
        return 95.0
    if T >= 35.0:
        return 70.0
    # 75% a 20°C, -0.4 %RH per °C circa
    return 75.0 - 0.4 * (T - 20.0)


def ri_muffa(features: RiskFeatures, ms: ManuscriptStatic, weights: Dict[str, float]) -> float:
    """
    RI_Muffa in % (frazione di ore-anno sopra LIM).

    `features.ore_sopra_LIM_anno` è già il dato osservato; viene normalizzato
    sulle 8760 ore annue. Soglie: 3% attenzione, 5% critica.
    """
    raw = 100.0 * features.ore_sopra_LIM_anno / 8760.0
    env_mod = 1.0 + 0.3 * (weights.get("rischio_muffa_LIM", 0.5) - 0.5)
    return _clip100(raw * env_mod)


# ---------------------------------------------------------------------------
# RI_Fotodeterioramento  —  ΔE* atteso a 5 anni
# ---------------------------------------------------------------------------
def ri_fotodeterioramento(
    features: RiskFeatures, ms: ManuscriptStatic, weights: Dict[str, float]
) -> float:
    """
    Restituisce il ΔE* atteso a 5 anni di esposizione cumulata.
    Banda nominale (D4.2.2.2):
      Basso        : 5–20
      Medio        : 20–40
      Alto         : 40–80
      Molto Alto   : 80–130
    """
    # Dose cumulata in lux·h sui 5 anni proiettati
    dose = features.lux_cumulati_5anni  # lux·h
    # Calibrazione: 5e6 lux·h ≈ ΔE* 25 per pigmento generico
    # (riferimento ISO Blue Wool BWS3 ~ 1.2 Mlx·h per ΔE* 5)
    sensitivity = 2.0 if ms.pigmenti_fotosensibili else 1.0
    delta_E = sensitivity * (dose / 1.0e6) * 5.0
    # Pesatura dell'illuminamento ambientale
    delta_E *= 0.6 + 0.4 * weights.get("illuminamento", 0.5)
    return max(0.0, min(130.0, delta_E))


# ---------------------------------------------------------------------------
# RI_Totale (Michalski–Verticchio)
# ---------------------------------------------------------------------------
def ri_totale(
    ri_chim: float, ri_mecc: float, ri_ins: float, ri_muffa_v: float
) -> float:
    """RI_Totale in %, combinazione lineare standard."""
    raw = (
        RI_TOTAL_COEFS["RI_Chimico"] * ri_chim
        + RI_TOTAL_COEFS["RI_Meccanico"] * ri_mecc
        + RI_TOTAL_COEFS["RI_Insetti"] * ri_ins
        + RI_TOTAL_COEFS["RI_Muffa"] * ri_muffa_v
    )
    return _clip100(raw)


def severity_from_RI_totale(value: float) -> str:
    """Mappa RI_Totale → categoria di severità (verde/giallo/arancio/rosso)."""
    crit = RI_THRESHOLDS["RI_Totale"]["critica"]
    att = RI_THRESHOLDS["RI_Totale"]["attenzione"]
    if value >= crit:
        return "critico"
    if value >= att:
        return "attenzione"
    if value >= 20.0:
        return "accettabile"
    return "ottimale"


# ---------------------------------------------------------------------------
# Engine pubblico
# ---------------------------------------------------------------------------
def compute_all_indices(
    features: RiskFeatures,
    manuscript: ManuscriptStatic,
    environment_type: EnvironmentType | str,
    weights_override: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Calcola tutti gli indici per un manufatto in un dato ambiente.

    Args:
        features: feature aggregate dalla finestra di telemetria.
        manuscript: caratterizzazione codicologica statica.
        environment_type: tipologia ambiente (per look-up pesi).
        weights_override: pesi runtime (override matrice ambiente).

    Returns:
        Dict con i 5 RI elementari + RI_Totale + severity.
    """
    env_key = (
        environment_type.value if isinstance(environment_type, EnvironmentType) else environment_type
    )
    w = weights_override if weights_override is not None else DEFAULT_WEIGHTS[env_key]

    chim = ri_chimico(features, manuscript, w)
    mecc = ri_meccanico(features, manuscript, w)
    ins = ri_insetti(features, manuscript, w)
    muf = ri_muffa(features, manuscript, w)
    fot = ri_fotodeterioramento(features, manuscript, w)
    tot = ri_totale(chim, mecc, ins, muf)

    return {
        "RI_Chimico": round(chim, 2),
        "RI_Meccanico": round(mecc, 2),
        "RI_Insetti": round(ins, 2),
        "RI_Muffa": round(muf, 2),
        "RI_Fotodeterioramento": round(fot, 2),
        "RI_Totale": round(tot, 2),
        "severity": severity_from_RI_totale(tot),
    }


# ---------------------------------------------------------------------------
# Aggregazione di feature da serie storica grezza
# ---------------------------------------------------------------------------
def aggregate_features(
    series: Iterable[Dict],
    *,
    fragilita_band_T: tuple[float, float] = (16.0, 22.0),
    fragilita_band_RH: tuple[float, float] = (45.0, 60.0),
) -> RiskFeatures:
    """
    Calcola le feature finestrate a partire da una sequenza di campioni
    (lista di dict con T, RH, lux, VOC, PM10, ...).

    `fragilita_band_*` definisce la banda EN 15757 storicizzata per il manufatto.
    """
    arr = list(series)
    if not arr:
        # Default neutro
        return RiskFeatures(
            T_media_24h=20.0, T_media_30gg=20.0,
            RH_media_24h=50.0, RH_media_30gg=50.0,
            dT_24h=0.0, dRH_24h=0.0, dRH_30gg=0.0,
            lux_medio=0.0, lux_cumulati_5anni=0.0,
            VOC_medio_24h=0.0, PM10_medio_24h=0.0,
            gradiente_verticale_T=0.0,
            ore_sopra_LIM_anno=0.0, frazione_fuori_EN15757=0.0,
        )

    T = np.array([s["T"] for s in arr], dtype=float)
    RH = np.array([s["RH"] for s in arr], dtype=float)
    lux = np.array([s.get("lux", 0.0) for s in arr], dtype=float)
    VOC = np.array([s.get("VOC", 0.0) for s in arr], dtype=float)
    PM10 = np.array([s.get("PM10", 0.0) for s in arr], dtype=float)

    # Stima della granularità: assumiamo ≥ 24 campioni per giornata se freq ≥ 1h
    n = len(arr)
    last24 = max(1, min(n, 144))   # 144 = 24h * 6 (10 min)
    last30d = n  # tutta la finestra fornita

    T_24 = float(T[-last24:].mean())
    T_30 = float(T.mean())
    RH_24 = float(RH[-last24:].mean())
    RH_30 = float(RH.mean())
    dT24 = float(T[-last24:].max() - T[-last24:].min())
    dRH24 = float(RH[-last24:].max() - RH[-last24:].min())
    dRH30 = float(RH.max() - RH.min())

    # Dose luminosa: media nelle ore con lux>0 × 8h × 365 × 5 (anni)
    lux_active = lux[lux > 1.0]
    lux_mean_active = float(lux_active.mean()) if lux_active.size else 0.0
    duty = (lux > 1.0).mean()  # frazione di ore "accese"
    lux_cum_5y = lux_mean_active * duty * 24.0 * 365.0 * 5.0  # lux·h

    # Ore sopra LIM Sedlbauer normalizzate su anno
    over = 0
    for t_i, rh_i in zip(T, RH):
        if rh_i > sedlbauer_LIM(t_i):
            over += 1
    # Riproporzionamento all'anno (8760 h) assumendo campioni ad 1 ora
    # Per granularità 10 min, scalare di 1/6
    sample_hours = max(0.1, n / 8760.0)  # quante ore-anno contiene la finestra
    ore_sopra_LIM_anno = over / max(1, n) * 8760.0

    # EN 15757 storicizzato — frazione fuori banda
    band_T_lo, band_T_hi = fragilita_band_T
    band_RH_lo, band_RH_hi = fragilita_band_RH
    out_T = ((T < band_T_lo) | (T > band_T_hi)).mean()
    out_RH = ((RH < band_RH_lo) | (RH > band_RH_hi)).mean()
    frac_out = float(max(out_T, out_RH))

    # Gradiente verticale T se presente nei dati (sala storica)
    grad = 0.0
    if any(s.get("quota") for s in arr):
        T_pt = np.array([s["T"] for s in arr if s.get("quota") == "piano_terra"])
        T_sp = np.array([s["T"] for s in arr if s.get("quota") == "soppalco"])
        if T_pt.size and T_sp.size:
            grad = float(T_sp.mean() - T_pt.mean())

    return RiskFeatures(
        T_media_24h=T_24,
        T_media_30gg=T_30,
        RH_media_24h=RH_24,
        RH_media_30gg=RH_30,
        dT_24h=dT24,
        dRH_24h=dRH24,
        dRH_30gg=dRH30,
        lux_medio=lux_mean_active,
        lux_cumulati_5anni=lux_cum_5y,
        VOC_medio_24h=float(VOC[-last24:].mean()),
        PM10_medio_24h=float(PM10[-last24:].mean()),
        gradiente_verticale_T=grad,
        ore_sopra_LIM_anno=ore_sopra_LIM_anno,
        frazione_fuori_EN15757=frac_out,
    )
