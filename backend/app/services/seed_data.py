"""
Seed dei dati demo VoH:
  - 4 ambienti (uno per tipo)
  - 8 manoscritti (2 per ambiente) con caratterizzazione codicologica realistica
  - 90 giorni di storico telemetrie nominali per ogni ambiente

Lo storico viene salvato in `backend/data/history_<environment_id>.csv` in
modo da non doverlo rigenerare ad ogni avvio.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from app.core.constants import EnvironmentType
from app.models.schemas import (
    AltezzaPavimento,
    Environment,
    FrequenzaConsultazione,
    InerziaTermoIgrometrica,
    Manuscript,
    Posizione,
    Quota,
    StatoLegatura,
    TipologiaSupporto,
)
from app.services.simulator import TelemetrySimulator


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Ambienti tipo
# ---------------------------------------------------------------------------
ENVIRONMENTS: List[Environment] = [
    Environment(
        id="ENV-ARM-01",
        nome="Armadio climatizzato — Sala A",
        tipo=EnvironmentType.ARMADIO_CHIUSO,
        inerzia_termo_igrometrica=InerziaTermoIgrometrica.ALTA,
    ),
    Environment(
        id="ENV-BIB-01",
        nome="Biblioteca di consultazione — Sala studiosi",
        tipo=EnvironmentType.BIBLIOTECA,
        inerzia_termo_igrometrica=InerziaTermoIgrometrica.MEDIA,
    ),
    Environment(
        id="ENV-DEP-01",
        nome="Deposito sotterraneo — Cripta nord",
        tipo=EnvironmentType.DEPOSITO_SOTTERRANEO,
        inerzia_termo_igrometrica=InerziaTermoIgrometrica.ALTA,
    ),
    Environment(
        id="ENV-SAL-01",
        nome="Sala storica monumentale — P.T. + Soppalco",
        tipo=EnvironmentType.SALA_STORICA,
        inerzia_termo_igrometrica=InerziaTermoIgrometrica.BASSA,
    ),
]


# ---------------------------------------------------------------------------
# Manoscritti precaricati (2 per ambiente)
# ---------------------------------------------------------------------------
MANUSCRIPTS: List[Manuscript] = [
    # --- Armadio chiuso ---
    Manuscript(
        id="MS-5463",
        nome="Codex Beneventanus — Vat. lat. 5463",
        tipologia_supporto=TipologiaSupporto.PERGAMENA,
        pH_stimato=6.2, DP0_stimato=1100,
        inchiostro_ferro_gallico=True,
        pigmenti_fotosensibili=False,
        stato_legatura=StatoLegatura.RESTAURATO,
        deformazioni_osservate=1, fragilita_osservata=1, alterazioni_cromatiche=1,
        frequenza_consultazione=FrequenzaConsultazione.RARA,
        ambiente_id="ENV-ARM-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.MEDIA,
            quota=Quota.PIANO_TERRA,
            parete_esterna=False, esposizione_solare=False,
        ),
    ),
    Manuscript(
        id="MS-0428",
        nome="Virgili Beneventani — frammento Aen.",
        tipologia_supporto=TipologiaSupporto.PERGAMENA,
        pH_stimato=5.8, DP0_stimato=950,
        inchiostro_ferro_gallico=True,
        pigmenti_fotosensibili=True,
        stato_legatura=StatoLegatura.FRAGILE,
        deformazioni_osservate=2, fragilita_osservata=2, alterazioni_cromatiche=2,
        frequenza_consultazione=FrequenzaConsultazione.RARA,
        ambiente_id="ENV-ARM-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.MEDIA,
            quota=Quota.PIANO_TERRA,
            parete_esterna=False, esposizione_solare=False,
        ),
    ),
    # --- Biblioteca ---
    Manuscript(
        id="MS-1190",
        nome="Pontificale di Beneventum — XII sec.",
        tipologia_supporto=TipologiaSupporto.PERGAMENA,
        pH_stimato=6.5, DP0_stimato=1300,
        inchiostro_ferro_gallico=True,
        pigmenti_fotosensibili=True,
        stato_legatura=StatoLegatura.BUONO,
        deformazioni_osservate=0, fragilita_osservata=1, alterazioni_cromatiche=1,
        frequenza_consultazione=FrequenzaConsultazione.OCCASIONALE,
        ambiente_id="ENV-BIB-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.ALTA,
            quota=Quota.PIANO_TERRA,
            parete_esterna=False, esposizione_solare=True,
        ),
    ),
    Manuscript(
        id="MS-2310",
        nome="Antifonario miniato — XIV sec.",
        tipologia_supporto=TipologiaSupporto.PERGAMENA,
        pH_stimato=6.0, DP0_stimato=1050,
        inchiostro_ferro_gallico=False,
        pigmenti_fotosensibili=True,
        stato_legatura=StatoLegatura.BUONO,
        deformazioni_osservate=1, fragilita_osservata=1, alterazioni_cromatiche=2,
        frequenza_consultazione=FrequenzaConsultazione.FREQUENTE,
        ambiente_id="ENV-BIB-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.MEDIA,
            quota=Quota.PIANO_TERRA,
            parete_esterna=True, esposizione_solare=True,
        ),
    ),
    # --- Deposito sotterraneo ---
    Manuscript(
        id="MS-7811",
        nome="Cartulario di S. Sofia — XI sec.",
        tipologia_supporto=TipologiaSupporto.PERGAMENA,
        pH_stimato=5.5, DP0_stimato=850,
        inchiostro_ferro_gallico=True,
        pigmenti_fotosensibili=False,
        stato_legatura=StatoLegatura.COMPROMESSO,
        deformazioni_osservate=2, fragilita_osservata=3, alterazioni_cromatiche=2,
        frequenza_consultazione=FrequenzaConsultazione.RARA,
        ambiente_id="ENV-DEP-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.BASSA,
            quota=Quota.PIANO_TERRA,
            parete_esterna=True, esposizione_solare=False,
        ),
    ),
    Manuscript(
        id="MS-9245",
        nome="Liber Confraternitatis — sec. XVII",
        tipologia_supporto=TipologiaSupporto.CARTA_ACIDA,
        pH_stimato=4.6, DP0_stimato=520,
        inchiostro_ferro_gallico=True,
        pigmenti_fotosensibili=False,
        stato_legatura=StatoLegatura.FRAGILE,
        deformazioni_osservate=2, fragilita_osservata=3, alterazioni_cromatiche=3,
        frequenza_consultazione=FrequenzaConsultazione.RARA,
        ambiente_id="ENV-DEP-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.MEDIA,
            quota=Quota.PIANO_TERRA,
            parete_esterna=True, esposizione_solare=False,
        ),
    ),
    # --- Sala storica P.T. + Soppalco ---
    Manuscript(
        id="MS-3340",
        nome="Codex liturgicus — sec. XV",
        tipologia_supporto=TipologiaSupporto.PERGAMENA,
        pH_stimato=6.3, DP0_stimato=1200,
        inchiostro_ferro_gallico=True,
        pigmenti_fotosensibili=True,
        stato_legatura=StatoLegatura.RESTAURATO,
        deformazioni_osservate=1, fragilita_osservata=1, alterazioni_cromatiche=1,
        frequenza_consultazione=FrequenzaConsultazione.OCCASIONALE,
        ambiente_id="ENV-SAL-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.MEDIA,
            quota=Quota.PIANO_TERRA,
            parete_esterna=False, esposizione_solare=True,
        ),
    ),
    Manuscript(
        id="MS-3341",
        nome="Diario capitolare — sec. XVIII (soppalco)",
        tipologia_supporto=TipologiaSupporto.CARTA_STRACCIATA,
        pH_stimato=6.8, DP0_stimato=1400,
        inchiostro_ferro_gallico=False,
        pigmenti_fotosensibili=False,
        stato_legatura=StatoLegatura.BUONO,
        deformazioni_osservate=0, fragilita_osservata=1, alterazioni_cromatiche=1,
        frequenza_consultazione=FrequenzaConsultazione.OCCASIONALE,
        ambiente_id="ENV-SAL-01",
        posizione=Posizione(
            altezza_dal_pavimento=AltezzaPavimento.ALTA,
            quota=Quota.SOPPALCO,
            parete_esterna=True, esposizione_solare=True,
        ),
    ),
]


# ---------------------------------------------------------------------------
# Generazione storico 90 giorni
# ---------------------------------------------------------------------------
def history_path(environment_id: str) -> Path:
    return DATA_DIR / f"history_{environment_id}.csv"


def write_history_csv(samples: List[dict], path: Path) -> None:
    fieldnames = [
        "timestamp", "environment_id", "T", "RH", "lux", "UV",
        "PM2_5", "PM10", "VOC", "CO2", "quota",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in samples:
            writer.writerow({k: s.get(k, "") for k in fieldnames})


def generate_all_histories(days: int = 90, force: bool = False, seed: int = 42) -> dict[str, Path]:
    """Genera (o riusa, se già presenti) gli storici CSV per ciascun ambiente."""
    out: dict[str, Path] = {}
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for env in ENVIRONMENTS:
        path = history_path(env.id)
        if path.exists() and not force:
            out[env.id] = path
            continue
        sim = TelemetrySimulator(
            environment_id=env.id,
            environment_type=env.tipo,
            seed=seed + hash(env.id) % 1000,
            start_time=end,
        )
        samples = sim.generate_history(days=days)
        write_history_csv(samples, path)
        out[env.id] = path
    return out


def load_history(environment_id: str) -> List[dict]:
    """Legge lo storico CSV e lo ritorna come lista di dict tipizzati."""
    path = history_path(environment_id)
    if not path.exists():
        return []
    out: List[dict] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append({
                "timestamp": row["timestamp"],
                "environment_id": row["environment_id"],
                "T": float(row["T"]),
                "RH": float(row["RH"]),
                "lux": float(row["lux"]),
                "UV": float(row["UV"]) if row["UV"] else 0.0,
                "PM2_5": float(row["PM2_5"]) if row["PM2_5"] else 0.0,
                "PM10": float(row["PM10"]) if row["PM10"] else 0.0,
                "VOC": float(row["VOC"]) if row["VOC"] else 0.0,
                "CO2": float(row["CO2"]) if row["CO2"] else 0.0,
                "quota": row["quota"] or None,
            })
    return out


if __name__ == "__main__":
    paths = generate_all_histories(days=90, force=True)
    for env_id, p in paths.items():
        print(f"  → {env_id}: {p} ({p.stat().st_size // 1024} KB)")
