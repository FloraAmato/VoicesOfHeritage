"""
Generatore di telemetrie simulate per il sensore multiparametrico artunified.

Profili specifici per ciascun ambiente VoH:
  - armadio_chiuso         : T/RH stabili, VOC endogeni in deriva, eventi apertura.
  - biblioteca             : ciclo orario di apertura, picchi lux, ΔT/ΔRH alti nei
                             giorni di alta affluenza.
  - deposito_sotterraneo   : T molto stabile (14–18°C), RH cronicamente alta
                             (60–75%), eventi meteorici con picchi RH.
  - sala_storica_pt_soppalco : escursione stagionale ampia, doppia traccia P.T./
                             soppalco con offset realistici.

Modalità "scenario": iniezione di pattern A–E (Tabella 4 D4.2.2.2) per la demo.

Output: lista di TelemetrySample serializzabili o stream WebSocket. La frequenza
di base è 10 minuti (144 campioni/giorno), comprimibile a 1 minuto in modalità
demo (vedi DEMO_TIME_COMPRESSION).

Decisione progettuale: il simulatore è deterministico se passato `seed`, così
gli storici precaricati sono riproducibili.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterator, List, Optional

import numpy as np

from app.core.constants import EnvironmentType


SAMPLE_INTERVAL_MIN = 10  # campioni nominali ogni 10 minuti
SAMPLES_PER_DAY = (24 * 60) // SAMPLE_INTERVAL_MIN  # 144

DEMO_TIME_COMPRESSION = 10  # in modalità demo 1 minuto reale = 10 minuti simulati


class Scenario(str, Enum):
    NONE = "none"
    A_PICCO_RH = "A"            # Picco RH in deposito
    B_OSCILL_T = "B"            # Oscillazioni T rapide in sala storica
    C_VOC = "C"                 # Saturazione VOC in armadio
    D_LUX = "D"                 # Esposizione luminosa in biblioteca
    E_STRATIFICAZIONE = "E"     # Gradiente verticale in sala storica soppalco


# ---------------------------------------------------------------------------
# Profili nominali per ambiente
# ---------------------------------------------------------------------------
@dataclass
class EnvProfile:
    T_mean: float           # °C — media stagionale di base
    T_amp_seasonal: float   # °C — semi-ampiezza ciclo annuale
    T_amp_diurnal: float    # °C — semi-ampiezza ciclo giornaliero
    T_noise: float          # °C — std del rumore
    RH_mean: float          # %
    RH_amp_seasonal: float  # %
    RH_amp_diurnal: float   # %
    RH_noise: float         # %
    lux_day_mean: float     # lux — illuminamento medio nelle ore di "luce"
    lux_active_hours: tuple = (0, 0)  # (h_start, h_end) range orario
    voc_baseline: float = 100.0
    voc_drift_per_day: float = 0.0
    pm10_mean: float = 12.0
    co2_mean: float = 450.0
    inertia: float = 0.85   # smoothing AR(1) — alta inerzia → bassa variabilità
    # Solo per sala storica:
    soppalco_T_offset: float = 0.0
    soppalco_RH_offset: float = 0.0


PROFILES: dict[str, EnvProfile] = {
    EnvironmentType.ARMADIO_CHIUSO.value: EnvProfile(
        T_mean=20.0, T_amp_seasonal=1.0, T_amp_diurnal=0.3, T_noise=0.08,
        RH_mean=50.0, RH_amp_seasonal=3.0, RH_amp_diurnal=0.8, RH_noise=0.4,
        lux_day_mean=0.0, lux_active_hours=(0, 0),
        voc_baseline=180.0, voc_drift_per_day=2.5,
        pm10_mean=4.0, co2_mean=500.0,
        inertia=0.96,
    ),
    EnvironmentType.BIBLIOTECA.value: EnvProfile(
        T_mean=21.0, T_amp_seasonal=2.5, T_amp_diurnal=1.0, T_noise=0.18,
        RH_mean=50.0, RH_amp_seasonal=6.0, RH_amp_diurnal=2.5, RH_noise=1.0,
        lux_day_mean=180.0, lux_active_hours=(9, 18),
        voc_baseline=250.0, voc_drift_per_day=0.0,
        pm10_mean=18.0, co2_mean=700.0,
        inertia=0.80,
    ),
    EnvironmentType.DEPOSITO_SOTTERRANEO.value: EnvProfile(
        T_mean=16.0, T_amp_seasonal=0.6, T_amp_diurnal=0.1, T_noise=0.05,
        RH_mean=68.0, RH_amp_seasonal=5.0, RH_amp_diurnal=0.5, RH_noise=0.6,
        lux_day_mean=0.0, lux_active_hours=(0, 0),
        voc_baseline=150.0, voc_drift_per_day=0.0,
        pm10_mean=8.0, co2_mean=550.0,
        inertia=0.97,
    ),
    EnvironmentType.SALA_STORICA.value: EnvProfile(
        T_mean=20.0, T_amp_seasonal=5.0, T_amp_diurnal=2.0, T_noise=0.25,
        RH_mean=50.0, RH_amp_seasonal=12.0, RH_amp_diurnal=4.0, RH_noise=1.5,
        lux_day_mean=120.0, lux_active_hours=(8, 19),
        voc_baseline=200.0, voc_drift_per_day=0.0,
        pm10_mean=22.0, co2_mean=600.0,
        inertia=0.70,
        soppalco_T_offset=2.0,    # +2 °C al soppalco
        soppalco_RH_offset=-6.5,  # -6.5 %RH al soppalco
    ),
}


# ---------------------------------------------------------------------------
# Generatore principale
# ---------------------------------------------------------------------------
class TelemetrySimulator:
    """
    Generatore stateful: tiene traccia del valore precedente per modellare
    inerzia AR(1). Supporta hook scenari (A–E) iniettabili a runtime.
    """

    def __init__(
        self,
        environment_id: str,
        environment_type: EnvironmentType | str,
        *,
        seed: Optional[int] = None,
        start_time: Optional[datetime] = None,
    ):
        self.environment_id = environment_id
        env_key = (
            environment_type.value if isinstance(environment_type, EnvironmentType) else environment_type
        )
        self.environment_type = env_key
        self.profile = PROFILES[env_key]
        self.rng = np.random.default_rng(seed)
        self._py_rng = random.Random(seed)
        self._t_state: Optional[float] = None
        self._rh_state: Optional[float] = None
        self._t_state_soppalco: Optional[float] = None
        self._rh_state_soppalco: Optional[float] = None
        self._voc_state: float = self.profile.voc_baseline
        self.now = start_time or datetime.now(timezone.utc).replace(microsecond=0)
        # Stato scenari
        self.active_scenario: Scenario = Scenario.NONE
        self._scenario_start: Optional[datetime] = None
        self._scenario_duration: timedelta = timedelta(hours=72)
        # Posa in atto degli "eventi apertura armadio" e "giornata affluenza"
        self._daily_event_seed = self._py_rng.random()

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------
    def trigger_scenario(self, scenario: Scenario, duration_hours: float = 72.0) -> None:
        """Attiva uno scenario demo a partire dal prossimo campione."""
        self.active_scenario = scenario
        self._scenario_start = self.now
        self._scenario_duration = timedelta(hours=duration_hours)

    def reset_scenario(self) -> None:
        self.active_scenario = Scenario.NONE
        self._scenario_start = None

    def step(self) -> dict | List[dict]:
        """
        Avanza di un campione (10 min). Restituisce un dict (singolo sensore)
        oppure una lista di 2 dict per la sala storica (P.T. + soppalco).
        """
        sample = self._generate_sample(self.now)
        self.now = self.now + timedelta(minutes=SAMPLE_INTERVAL_MIN)
        return sample

    def generate_history(self, days: int = 90) -> List[dict]:
        """Genera retroattivamente N giorni di storico terminanti in `self.now`."""
        n = days * SAMPLES_PER_DAY
        end = self.now
        start = end - timedelta(minutes=SAMPLE_INTERVAL_MIN * n)
        # Riavvolgi lo stato a `start` e poi avanza
        prev_now = self.now
        self.now = start
        out: List[dict] = []
        for _ in range(n):
            s = self.step()
            if isinstance(s, list):
                out.extend(s)
            else:
                out.append(s)
        self.now = prev_now
        return out

    def stream(self, max_samples: Optional[int] = None) -> Iterator[dict]:
        """Iteratore live."""
        i = 0
        while max_samples is None or i < max_samples:
            s = self.step()
            if isinstance(s, list):
                for ss in s:
                    yield ss
            else:
                yield s
            i += 1

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _seasonal(self, ts: datetime, amp: float, mean: float) -> float:
        """Componente stagionale annuale (massimo a fine luglio per T, antifase per RH)."""
        day_of_year = ts.timetuple().tm_yday
        return mean + amp * math.sin(2 * math.pi * (day_of_year - 110) / 365.0)

    def _diurnal(self, ts: datetime, amp: float) -> float:
        """Componente diurna: massimo intorno alle 14:00."""
        h = ts.hour + ts.minute / 60.0
        return amp * math.sin(2 * math.pi * (h - 8) / 24.0)

    def _ar1(self, prev: Optional[float], target: float, alpha: float, noise: float) -> float:
        """Smoothing AR(1) attorno al target con rumore gaussiano."""
        if prev is None:
            return target + self.rng.normal(0.0, noise)
        return alpha * prev + (1.0 - alpha) * target + self.rng.normal(0.0, noise)

    def _scenario_active(self, ts: datetime) -> bool:
        if self.active_scenario == Scenario.NONE or self._scenario_start is None:
            return False
        return ts <= self._scenario_start + self._scenario_duration

    def _scenario_progress(self, ts: datetime) -> float:
        """Frazione [0,1] di completamento dello scenario corrente."""
        if not self._scenario_active(ts):
            return 0.0
        elapsed = (ts - self._scenario_start).total_seconds()
        total = self._scenario_duration.total_seconds()
        return max(0.0, min(1.0, elapsed / total))

    def _is_open_hours(self, ts: datetime) -> bool:
        h0, h1 = self.profile.lux_active_hours
        if h0 == h1:
            return False
        return h0 <= ts.hour < h1 and ts.weekday() < 6  # chiuso domenica

    def _generate_sample(self, ts: datetime):
        p = self.profile

        # --- Componenti stagionali e diurne ---
        T_target = self._seasonal(ts, p.T_amp_seasonal, p.T_mean) + self._diurnal(ts, p.T_amp_diurnal)
        # RH antifase con T (estate più secca al chiuso climatizzato)
        RH_target = (
            self._seasonal(ts, -p.RH_amp_seasonal, p.RH_mean)
            + self._diurnal(ts, -p.RH_amp_diurnal)
        )

        # --- Eventi specifici per ambiente ---
        T_target, RH_target, lux_extra, voc_extra = self._apply_environment_events(
            ts, T_target, RH_target
        )

        # --- Iniezione scenario demo ---
        T_target, RH_target, lux_extra, voc_extra = self._apply_scenario(
            ts, T_target, RH_target, lux_extra, voc_extra
        )

        # --- AR(1) ---
        T = self._ar1(self._t_state, T_target, p.inertia, p.T_noise)
        RH = self._ar1(self._rh_state, RH_target, p.inertia, p.RH_noise)
        self._t_state = T
        self._rh_state = RH

        # --- Lux ---
        if self._is_open_hours(ts):
            base_lux = p.lux_day_mean * (0.7 + 0.6 * self.rng.random())
        else:
            base_lux = 0.0
        lux = max(0.0, base_lux + lux_extra)
        UV = lux * 0.05  # µW/lumen approssimativo per illuminazione mista

        # --- VOC con deriva endogena (armadio chiuso accumula) ---
        days_since_start = (ts - (self._scenario_start or ts)).total_seconds() / 86400.0
        self._voc_state = max(
            50.0,
            self._voc_state + p.voc_drift_per_day * (SAMPLE_INTERVAL_MIN / 1440.0)
            + self.rng.normal(0.0, 5.0),
        )
        # Reset settimanale per simulare ricambio aria all'apertura
        if ts.weekday() == 0 and ts.hour == 9 and ts.minute < SAMPLE_INTERVAL_MIN:
            self._voc_state = max(50.0, self._voc_state * 0.6)
        VOC = self._voc_state + voc_extra

        PM10 = max(0.0, p.pm10_mean + self.rng.normal(0.0, 3.0))
        PM2_5 = PM10 * 0.55
        CO2 = p.co2_mean + (200.0 if self._is_open_hours(ts) else 0.0) + self.rng.normal(0.0, 30.0)

        sample = {
            "timestamp": ts.isoformat(),
            "environment_id": self.environment_id,
            "T": round(float(T), 3),
            "RH": round(float(RH), 2),
            "lux": round(float(lux), 1),
            "UV": round(float(UV), 2),
            "PM2_5": round(float(PM2_5), 2),
            "PM10": round(float(PM10), 2),
            "VOC": round(float(VOC), 1),
            "CO2": round(float(CO2), 1),
            "quota": None,
        }

        # --- Doppia traccia per sala storica ---
        if self.environment_type == EnvironmentType.SALA_STORICA.value:
            T_pt = float(T)
            RH_pt = float(RH)
            sample["quota"] = "piano_terra"
            sample["T"] = round(T_pt, 3)
            sample["RH"] = round(RH_pt, 2)

            # Soppalco: offset + AR(1) indipendente
            offset_T = p.soppalco_T_offset
            offset_RH = p.soppalco_RH_offset
            # In scenario E lo offset si amplifica
            if self.active_scenario == Scenario.E_STRATIFICAZIONE and self._scenario_active(ts):
                offset_T += 0.8 * self._scenario_progress(ts)
            T_sop_target = T_target + offset_T
            RH_sop_target = RH_target + offset_RH
            T_sop = self._ar1(self._t_state_soppalco, T_sop_target, p.inertia, p.T_noise)
            RH_sop = self._ar1(self._rh_state_soppalco, RH_sop_target, p.inertia, p.RH_noise)
            self._t_state_soppalco = T_sop
            self._rh_state_soppalco = RH_sop
            sample_soppalco = dict(sample)
            sample_soppalco.update({
                "T": round(float(T_sop), 3),
                "RH": round(float(RH_sop), 2),
                "quota": "soppalco",
            })
            return [sample, sample_soppalco]

        return sample

    # ------------------------------------------------------------------
    # Eventi specifici per ambiente
    # ------------------------------------------------------------------
    def _apply_environment_events(self, ts, T_target, RH_target):
        p = self.profile
        lux_extra = 0.0
        voc_extra = 0.0

        if self.environment_type == EnvironmentType.ARMADIO_CHIUSO.value:
            # Eventi di apertura: rare, +VOC trasciori
            if self.rng.random() < 1.0 / SAMPLES_PER_DAY * 0.3:  # ~0.3 aperture/giorno
                voc_extra += 80.0

        elif self.environment_type == EnvironmentType.BIBLIOTECA.value:
            # Giornate di alta affluenza (1 su 5): +ΔT, +ΔRH durante apertura
            if self._is_open_hours(ts) and (ts.toordinal() % 5 == 0):
                T_target += 0.6
                RH_target += 1.5

        elif self.environment_type == EnvironmentType.DEPOSITO_SOTTERRANEO.value:
            # Eventi meteorici: 1 ogni ~5 giorni, picco RH per 12h
            ev_seed = (ts.toordinal() * 13 + 7) % 100
            if ev_seed < 4:  # ~4% delle giornate hanno evento
                hours_since_midnight = ts.hour + ts.minute / 60.0
                if 4 < hours_since_midnight < 16:
                    bump = 4.0 * math.sin(math.pi * (hours_since_midnight - 4) / 12.0)
                    RH_target += bump

        elif self.environment_type == EnvironmentType.SALA_STORICA.value:
            # Picchi visite turistiche: weekend mattina
            if ts.weekday() >= 5 and 10 <= ts.hour < 13:
                T_target += 0.8
                RH_target += 2.0

        return T_target, RH_target, lux_extra, voc_extra

    # ------------------------------------------------------------------
    # Iniezione scenari A–E
    # ------------------------------------------------------------------
    def _apply_scenario(self, ts, T_target, RH_target, lux_extra, voc_extra):
        if not self._scenario_active(ts):
            return T_target, RH_target, lux_extra, voc_extra

        progress = self._scenario_progress(ts)
        s = self.active_scenario

        if s == Scenario.A_PICCO_RH and self.environment_type == EnvironmentType.DEPOSITO_SOTTERRANEO.value:
            # RH spinta sopra 65% per 48h+
            RH_target += 9.0 * progress  # da 68% sale verso 77%

        elif s == Scenario.B_OSCILL_T and self.environment_type == EnvironmentType.SALA_STORICA.value:
            # Oscillazioni rapide ΔT24h > 4°C: ciclo a 6h ampiezza ±3°C
            h = ts.hour + ts.minute / 60.0
            T_target += 3.0 * math.sin(2 * math.pi * h / 6.0) * (0.5 + 0.5 * progress)

        elif s == Scenario.C_VOC and self.environment_type == EnvironmentType.ARMADIO_CHIUSO.value:
            # Saturazione VOC: rampa fino a >1000 ppb
            voc_extra += 1000.0 * progress

        elif s == Scenario.D_LUX and self.environment_type == EnvironmentType.BIBLIOTECA.value:
            # Esposizione luminosa elevata su miniato (300+ lux durante apertura)
            if self._is_open_hours(ts):
                lux_extra += 200.0 * (0.5 + 0.5 * progress)

        elif s == Scenario.E_STRATIFICAZIONE and self.environment_type == EnvironmentType.SALA_STORICA.value:
            # Gestito direttamente nel ramo soppalco
            pass

        return T_target, RH_target, lux_extra, voc_extra


# ---------------------------------------------------------------------------
# Multi-environment orchestrator (per la dashboard)
# ---------------------------------------------------------------------------
@dataclass
class SimulatorRegistry:
    """Tiene gli oggetti TelemetrySimulator per ciascun ambiente attivo."""

    simulators: dict[str, TelemetrySimulator] = field(default_factory=dict)

    def register(self, sim: TelemetrySimulator) -> None:
        self.simulators[sim.environment_id] = sim

    def get(self, environment_id: str) -> TelemetrySimulator:
        return self.simulators[environment_id]

    def step_all(self) -> List[dict]:
        out: List[dict] = []
        for sim in self.simulators.values():
            s = sim.step()
            if isinstance(s, list):
                out.extend(s)
            else:
                out.append(s)
        return out

    def trigger(self, environment_id: str, scenario: Scenario, duration_hours: float = 72.0) -> None:
        self.simulators[environment_id].trigger_scenario(scenario, duration_hours)

    def reset_all(self) -> None:
        for sim in self.simulators.values():
            sim.reset_scenario()
