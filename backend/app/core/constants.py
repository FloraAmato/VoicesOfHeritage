"""
Costanti di dominio del sistema VoH.

Le matrici dei pesi e le soglie ambientali sono trascritte fedelmente dal
deliverable D4.2.2.2 (Tabella 1 — soglie ambientali, Tabella 3 — matrice pesi).
Modificarle a runtime via API /api/weights/{env_type}.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


# ---------------------------------------------------------------------------
# Tipologie di ambiente (4 contesti VoH)
# ---------------------------------------------------------------------------
class EnvironmentType(str, Enum):
    ARMADIO_CHIUSO = "armadio_chiuso"
    BIBLIOTECA = "biblioteca_consultazione"
    DEPOSITO_SOTTERRANEO = "deposito_sotterraneo"
    SALA_STORICA = "sala_storica_pt_soppalco"


# ---------------------------------------------------------------------------
# Matrice dei pesi ambiente-dipendenti (D4.2.2.2 — Tabella 3)
# Le variabili in grassetto nei deliverable sono evidenziate con peso ≥ 0.9.
# I pesi modulano i CONTRIBUTI delle variabili d'ingresso al calcolo dei singoli
# RI; non sono i coefficienti dell'aggregazione finale (cfr. RI_Totale).
# ---------------------------------------------------------------------------
WEIGHT_VARIABLES = (
    "T_media_24h",
    "RH_media_30gg",
    "dT_24h",
    "dRH_24h",
    "illuminamento",
    "PM_VOC",
    "gradiente_verticale_T",
    "rischio_muffa_LIM",
    "rischio_insetti",
)

DEFAULT_WEIGHTS: Dict[str, Dict[str, float]] = {
    EnvironmentType.ARMADIO_CHIUSO.value: {
        "T_media_24h": 0.4,
        "RH_media_30gg": 0.5,
        "dT_24h": 0.3,
        "dRH_24h": 0.4,
        "illuminamento": 0.1,
        "PM_VOC": 0.9,
        "gradiente_verticale_T": 0.1,
        "rischio_muffa_LIM": 0.6,
        "rischio_insetti": 0.7,
    },
    EnvironmentType.BIBLIOTECA.value: {
        "T_media_24h": 0.6,
        "RH_media_30gg": 0.7,
        "dT_24h": 0.7,
        "dRH_24h": 0.8,
        "illuminamento": 1.0,
        "PM_VOC": 0.6,
        "gradiente_verticale_T": 0.3,
        "rischio_muffa_LIM": 0.5,
        "rischio_insetti": 0.5,
    },
    EnvironmentType.DEPOSITO_SOTTERRANEO.value: {
        "T_media_24h": 0.3,
        "RH_media_30gg": 0.9,
        "dT_24h": 0.2,
        "dRH_24h": 0.3,
        "illuminamento": 0.1,
        "PM_VOC": 0.5,
        "gradiente_verticale_T": 0.2,
        "rischio_muffa_LIM": 1.0,
        "rischio_insetti": 0.9,
    },
    EnvironmentType.SALA_STORICA.value: {
        "T_media_24h": 0.8,
        "RH_media_30gg": 0.8,
        "dT_24h": 0.9,
        "dRH_24h": 1.0,
        "illuminamento": 0.9,
        "PM_VOC": 0.7,
        "gradiente_verticale_T": 1.0,
        "rischio_muffa_LIM": 0.7,
        "rischio_insetti": 0.8,
    },
}


# ---------------------------------------------------------------------------
# Soglie ambientali (D4.2.2.2 — Tabella 1)
# Ogni parametro ha 4 livelli: ottimale / accettabile / attenzione / critico.
# Per ciascun livello: tupla (min, max) — None significa illimitato in quella direzione.
# ---------------------------------------------------------------------------
THRESHOLDS: Dict[str, Dict[str, tuple]] = {
    # Temperatura aria (°C) — manoscritti pergamenacei e cartacei
    "T": {
        "ottimale": (16.0, 20.0),
        "accettabile": (14.0, 22.0),
        "attenzione": (10.0, 25.0),
        "critico": (None, None),  # qualsiasi valore fuori da attenzione
    },
    # Umidità relativa (%)
    "RH": {
        "ottimale": (45.0, 55.0),
        "accettabile": (40.0, 60.0),
        "attenzione": (35.0, 65.0),
        "critico": (None, None),
    },
    # Variazione T nelle 24h (°C) — fluttuazioni meccaniche
    "dT_24h": {
        "ottimale": (0.0, 1.5),
        "accettabile": (0.0, 2.5),
        "attenzione": (0.0, 4.0),
        "critico": (4.0, None),
    },
    # Variazione RH nelle 24h (%)
    "dRH_24h": {
        "ottimale": (0.0, 5.0),
        "accettabile": (0.0, 8.0),
        "attenzione": (0.0, 12.0),
        "critico": (12.0, None),
    },
    # Illuminamento (lux) — manoscritti miniati / fotosensibili
    "lux": {
        "ottimale": (0.0, 50.0),
        "accettabile": (0.0, 150.0),
        "attenzione": (0.0, 300.0),
        "critico": (300.0, None),
    },
    # UV (µW/lumen)
    "UV": {
        "ottimale": (0.0, 30.0),
        "accettabile": (0.0, 75.0),
        "attenzione": (0.0, 150.0),
        "critico": (150.0, None),
    },
    # PM10 (µg/m³)
    "PM10": {
        "ottimale": (0.0, 20.0),
        "accettabile": (0.0, 40.0),
        "attenzione": (0.0, 75.0),
        "critico": (75.0, None),
    },
    # VOC (ppb)
    "VOC": {
        "ottimale": (0.0, 200.0),
        "accettabile": (0.0, 500.0),
        "attenzione": (0.0, 1000.0),
        "critico": (1000.0, None),
    },
}


# ---------------------------------------------------------------------------
# Soglie sugli indici di rischio (D4.2.2.2 — cap. 6)
# ---------------------------------------------------------------------------
RI_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "RI_Chimico": {"attenzione": 40.0, "critica": 60.0},
    "RI_Meccanico": {"attenzione": 1.0, "critica": 2.0},
    "RI_Insetti": {"attenzione": 35.0, "critica": 50.0},
    "RI_Muffa": {"attenzione": 3.0, "critica": 5.0},
    "RI_Fotodeterioramento": {"attenzione": 40.0, "critica": 80.0},
    "RI_Totale": {"attenzione": 35.0, "critica": 50.0},
}


# Coefficienti di aggregazione per RI_Totale (Michalski–Verticchio)
RI_TOTAL_COEFS = {
    "RI_Chimico": 0.50,
    "RI_Meccanico": 0.10,
    "RI_Insetti": 0.25,
    "RI_Muffa": 0.15,
}


# Severity color codes (per frontend, mantenute backend-side per coerenza)
SEVERITY_COLORS = {
    "ottimale": "#16a34a",   # verde
    "accettabile": "#84cc16",  # verde chiaro
    "attenzione": "#f59e0b",  # arancio
    "critico": "#dc2626",     # rosso
}
