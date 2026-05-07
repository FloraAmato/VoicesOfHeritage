"""
Pydantic schemas — modello dati VoH.

I campi del Manuscript derivano dal questionario codicologico in Allegato A
del D4.2.2.2 e sono usati come parametrizzazione iniziale (caratterizzazione
statica) per la pesatura delle variabili ambientali.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import EnvironmentType


# ---------------------------------------------------------------------------
# Enumerazioni codicologiche
# ---------------------------------------------------------------------------
class TipologiaSupporto(str, Enum):
    PERGAMENA = "pergamena"
    CARTA_STRACCIATA = "carta_stracciata"
    CARTA_ACIDA = "carta_acida"
    CARTA_ALCALINA = "carta_alcalina"


class StatoLegatura(str, Enum):
    BUONO = "buono"
    FRAGILE = "fragile"
    RESTAURATO = "restaurato"
    COMPROMESSO = "compromesso"


class FrequenzaConsultazione(str, Enum):
    RARA = "rara"
    OCCASIONALE = "occasionale"
    FREQUENTE = "frequente"


class AltezzaPavimento(str, Enum):
    BASSA = "<1m"
    MEDIA = "1-2m"
    ALTA = ">2m"


class Quota(str, Enum):
    PIANO_TERRA = "piano_terra"
    SOPPALCO = "soppalco"


class InerziaTermoIgrometrica(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BASSA = "bassa"


# ---------------------------------------------------------------------------
# Posizione fisica del manufatto nel contenitore/sala
# ---------------------------------------------------------------------------
class Posizione(BaseModel):
    altezza_dal_pavimento: AltezzaPavimento
    quota: Quota
    parete_esterna: bool = False
    esposizione_solare: bool = False


# ---------------------------------------------------------------------------
# Ambiente
# ---------------------------------------------------------------------------
class Environment(BaseModel):
    id: str
    nome: str
    tipo: EnvironmentType
    inerzia_termo_igrometrica: InerziaTermoIgrometrica


# ---------------------------------------------------------------------------
# Manoscritto
# ---------------------------------------------------------------------------
class Manuscript(BaseModel):
    id: str = Field(..., examples=["MS-5463"])
    nome: str
    tipologia_supporto: TipologiaSupporto
    pH_stimato: float = Field(..., ge=4.0, le=8.5)
    DP0_stimato: int = Field(..., ge=200, le=2500)
    inchiostro_ferro_gallico: bool = False
    pigmenti_fotosensibili: bool = False
    stato_legatura: StatoLegatura
    deformazioni_osservate: int = Field(..., ge=0, le=3)
    fragilita_osservata: int = Field(..., ge=0, le=3)
    alterazioni_cromatiche: int = Field(..., ge=0, le=3)
    frequenza_consultazione: FrequenzaConsultazione
    ambiente_id: str
    posizione: Posizione


# ---------------------------------------------------------------------------
# Telemetria: campione singolo dal sensore multiparametrico artunified
# ---------------------------------------------------------------------------
class TelemetrySample(BaseModel):
    timestamp: datetime
    environment_id: str
    T: float                # °C
    RH: float               # %
    lux: float              # lux
    UV: float = 0.0         # µW/lumen
    PM2_5: float = 0.0      # µg/m³
    PM10: float = 0.0       # µg/m³
    VOC: float = 0.0        # ppb
    CO2: float = 400.0      # ppm
    # Per la sala storica con doppio sensore P.T./soppalco:
    quota: Optional[Quota] = None


# ---------------------------------------------------------------------------
# Indici di rischio (output del motore di rischio)
# ---------------------------------------------------------------------------
class RiskIndices(BaseModel):
    manuscript_id: str
    timestamp: datetime
    RI_Chimico: float
    RI_Meccanico: float
    RI_Insetti: float
    RI_Muffa: float
    RI_Fotodeterioramento: float
    RI_Totale: float
    severity: str  # "ottimale" | "accettabile" | "attenzione" | "critico"


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------
class AlertSeverity(str, Enum):
    INFO = "INFO"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class AlertStatus(str, Enum):
    APERTO = "aperto"
    PRESO_IN_CARICO = "preso_in_carico"
    RISOLTO = "risolto"


class Alert(BaseModel):
    id: str
    timestamp: datetime
    severity: AlertSeverity
    manuscript_id: str
    environment_id: str
    trigger_variable: str
    trigger_value: float
    RI_Totale: float
    message: str
    recommendation_id: Optional[str] = None
    status: AlertStatus = AlertStatus.APERTO
    note: Optional[str] = None
