"""Test del simulatore di telemetrie e dei profili ambientali."""

from datetime import datetime, timezone

import pytest

from app.core.constants import EnvironmentType
from app.services.simulator import (
    SAMPLES_PER_DAY,
    PROFILES,
    Scenario,
    TelemetrySimulator,
)


@pytest.fixture
def t0() -> datetime:
    return datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)


def test_profiles_cover_all_envs():
    expected = {e.value for e in EnvironmentType}
    assert set(PROFILES.keys()) == expected


def test_armadio_chiuso_stable_T(t0):
    sim = TelemetrySimulator("ENV-1", EnvironmentType.ARMADIO_CHIUSO, seed=1, start_time=t0)
    samples = list(sim.stream(max_samples=SAMPLES_PER_DAY))
    Ts = [s["T"] for s in samples]
    # In armadio: T deve oscillare poco (<1.5°C giornalieri)
    assert max(Ts) - min(Ts) < 1.5


def test_biblioteca_lux_during_open_hours(t0):
    # 1 maggio 2026 è venerdì → biblioteca aperta
    sim = TelemetrySimulator("ENV-2", EnvironmentType.BIBLIOTECA, seed=2, start_time=t0)
    # Avanzo fino alle 12:00
    for _ in range(12 * 6):
        sim.step()
    s = sim.step()
    assert s["lux"] > 50.0  # luce di lavoro


def test_deposito_high_RH(t0):
    sim = TelemetrySimulator("ENV-3", EnvironmentType.DEPOSITO_SOTTERRANEO, seed=3, start_time=t0)
    samples = list(sim.stream(max_samples=SAMPLES_PER_DAY * 7))
    rh_mean = sum(s["RH"] for s in samples) / len(samples)
    # Deposito sotterraneo: RH cronicamente alta
    assert 60.0 <= rh_mean <= 76.0


def test_sala_storica_emits_two_samples(t0):
    sim = TelemetrySimulator("ENV-4", EnvironmentType.SALA_STORICA, seed=4, start_time=t0)
    out = sim.step()
    assert isinstance(out, list)
    assert len(out) == 2
    quotas = {s["quota"] for s in out}
    assert quotas == {"piano_terra", "soppalco"}
    # Soppalco deve essere più caldo
    pt = next(s for s in out if s["quota"] == "piano_terra")
    sp = next(s for s in out if s["quota"] == "soppalco")
    # Con AR(1) al primo step possono coincidere; verifichiamo su una finestra
    diffs = []
    for _ in range(SAMPLES_PER_DAY):
        out = sim.step()
        pt_v = next(s for s in out if s["quota"] == "piano_terra")["T"]
        sp_v = next(s for s in out if s["quota"] == "soppalco")["T"]
        diffs.append(sp_v - pt_v)
    assert sum(diffs) / len(diffs) > 0.5  # in media il soppalco è più caldo


def test_scenario_A_picco_RH(t0):
    sim = TelemetrySimulator("ENV-3", EnvironmentType.DEPOSITO_SOTTERRANEO, seed=5, start_time=t0)
    # Baseline 24h
    base = list(sim.stream(max_samples=SAMPLES_PER_DAY))
    rh_base = sum(s["RH"] for s in base) / len(base)
    # Trigger
    sim.trigger_scenario(Scenario.A_PICCO_RH, duration_hours=72)
    after = []
    for _ in range(SAMPLES_PER_DAY * 3):
        after.append(sim.step())
    rh_after = sum(s["RH"] for s in after[-SAMPLES_PER_DAY:]) / SAMPLES_PER_DAY
    assert rh_after > rh_base + 4.0


def test_scenario_C_VOC_spike(t0):
    sim = TelemetrySimulator("ENV-1", EnvironmentType.ARMADIO_CHIUSO, seed=6, start_time=t0)
    # Avanzo 1 giorno per stabilizzare
    list(sim.stream(max_samples=SAMPLES_PER_DAY))
    voc_before = sim._voc_state
    sim.trigger_scenario(Scenario.C_VOC, duration_hours=72)
    samples = list(sim.stream(max_samples=SAMPLES_PER_DAY * 3))
    voc_peak = max(s["VOC"] for s in samples)
    assert voc_peak > 1000.0


def test_history_length(t0):
    sim = TelemetrySimulator("ENV-1", EnvironmentType.ARMADIO_CHIUSO, seed=7, start_time=t0)
    h = sim.generate_history(days=7)
    assert len(h) == 7 * SAMPLES_PER_DAY


def test_seed_reproducibility(t0):
    s1 = TelemetrySimulator("X", EnvironmentType.BIBLIOTECA, seed=42, start_time=t0)
    s2 = TelemetrySimulator("X", EnvironmentType.BIBLIOTECA, seed=42, start_time=t0)
    a = list(s1.stream(max_samples=10))
    b = list(s2.stream(max_samples=10))
    assert [x["T"] for x in a] == [x["T"] for x in b]
