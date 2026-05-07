"""
Test sui motori degli indici di rischio.
Coprono: f(pH), Brimblecombe, Sedlbauer, RI elementari, RI_Totale,
mappa severità.
"""

import math

import pytest

from app.core.constants import EnvironmentType, RI_THRESHOLDS
from app.services.risk_indices import (
    ManuscriptStatic,
    RiskFeatures,
    aggregate_features,
    brimblecombe_eggs_per_year,
    compute_all_indices,
    f_pH,
    ri_chimico,
    ri_fotodeterioramento,
    ri_insetti,
    ri_meccanico,
    ri_muffa,
    ri_totale,
    sedlbauer_LIM,
    severity_from_RI_totale,
)


# ---------- Funzioni atomiche ---------------------------------------------------


def test_fpH_endpoints():
    """f(pH=5)=0.55 e f(pH=7)=0.72 (D4.2.2.2 §6.1)."""
    assert math.isclose(f_pH(5.0), 0.55, abs_tol=1e-9)
    assert math.isclose(f_pH(7.0), 0.72, abs_tol=1e-9)


def test_fpH_monotonic():
    assert f_pH(5.5) < f_pH(6.0) < f_pH(6.5)


def test_brimblecombe_peak_at_29():
    """Il polinomio di Brimblecombe ha massimo ~1560 a T=29°C, RH=70%."""
    eggs = brimblecombe_eggs_per_year(29.0, 70.0)
    assert math.isclose(eggs, 1560.0, abs_tol=1.0)


def test_brimblecombe_zero_below_RH50():
    assert brimblecombe_eggs_per_year(29.0, 45.0) == 0.0


def test_brimblecombe_decreases_far_from_peak():
    peak = brimblecombe_eggs_per_year(29.0, 70.0)
    assert brimblecombe_eggs_per_year(15.0, 70.0) < peak * 0.05
    assert brimblecombe_eggs_per_year(29.0, 90.0) < peak


def test_sedlbauer_LIM_at_20C():
    assert math.isclose(sedlbauer_LIM(20.0), 75.0, abs_tol=0.01)


def test_sedlbauer_LIM_decreases_with_T():
    assert sedlbauer_LIM(15.0) > sedlbauer_LIM(20.0) > sedlbauer_LIM(25.0)


# ---------- Fixtures ------------------------------------------------------------


@pytest.fixture
def good_features() -> RiskFeatures:
    """Condizioni ottimali in armadio chiuso."""
    return RiskFeatures(
        T_media_24h=19.0, T_media_30gg=19.0,
        RH_media_24h=50.0, RH_media_30gg=50.0,
        dT_24h=1.0, dRH_24h=3.0, dRH_30gg=5.0,
        lux_medio=20.0, lux_cumulati_5anni=2.0e5,
        VOC_medio_24h=100.0, PM10_medio_24h=10.0,
        gradiente_verticale_T=0.0,
        ore_sopra_LIM_anno=0.0, frazione_fuori_EN15757=0.0,
    )


@pytest.fixture
def bad_features() -> RiskFeatures:
    """Condizioni critiche compatibili con un deposito sotterraneo umido."""
    return RiskFeatures(
        T_media_24h=24.0, T_media_30gg=24.0,
        RH_media_24h=78.0, RH_media_30gg=78.0,
        dT_24h=3.0, dRH_24h=10.0, dRH_30gg=20.0,
        lux_medio=0.0, lux_cumulati_5anni=0.0,
        VOC_medio_24h=600.0, PM10_medio_24h=40.0,
        gradiente_verticale_T=0.0,
        ore_sopra_LIM_anno=2000.0, frazione_fuori_EN15757=0.40,
    )


@pytest.fixture
def codex() -> ManuscriptStatic:
    """Codex pergamenaceo medievale tipico, ferro-gallico."""
    return ManuscriptStatic(
        pH=5.5, DP0=900,
        inchiostro_ferro_gallico=True,
        pigmenti_fotosensibili=False,
        fragilita=1,
    )


# ---------- RI elementari -------------------------------------------------------


def test_ri_chimico_increases_with_T(codex):
    f_low = RiskFeatures(
        T_media_24h=18.0, T_media_30gg=18.0, RH_media_24h=50.0, RH_media_30gg=50.0,
        dT_24h=1.0, dRH_24h=3.0, dRH_30gg=5.0,
        lux_medio=0.0, lux_cumulati_5anni=0.0,
        VOC_medio_24h=200.0, PM10_medio_24h=10.0,
        gradiente_verticale_T=0.0,
        ore_sopra_LIM_anno=0.0, frazione_fuori_EN15757=0.0,
    )
    f_hi = RiskFeatures(**{**f_low.__dict__, "T_media_30gg": 26.0})
    from app.core.constants import DEFAULT_WEIGHTS
    w = DEFAULT_WEIGHTS[EnvironmentType.BIBLIOTECA.value]
    assert ri_chimico(f_hi, codex, w) > ri_chimico(f_low, codex, w)


def test_ri_meccanico_increases_with_dRH(codex):
    f_low = RiskFeatures(
        T_media_24h=20.0, T_media_30gg=20.0, RH_media_24h=50.0, RH_media_30gg=50.0,
        dT_24h=1.0, dRH_24h=3.0, dRH_30gg=5.0,
        lux_medio=0.0, lux_cumulati_5anni=0.0,
        VOC_medio_24h=0.0, PM10_medio_24h=0.0,
        gradiente_verticale_T=0.0,
        ore_sopra_LIM_anno=0.0, frazione_fuori_EN15757=0.05,
    )
    f_hi = RiskFeatures(**{**f_low.__dict__, "dRH_24h": 15.0, "frazione_fuori_EN15757": 0.30})
    from app.core.constants import DEFAULT_WEIGHTS
    w = DEFAULT_WEIGHTS[EnvironmentType.SALA_STORICA.value]
    assert ri_meccanico(f_hi, codex, w) > ri_meccanico(f_low, codex, w)


def test_ri_insetti_peak_environment(codex, bad_features):
    from app.core.constants import DEFAULT_WEIGHTS
    w = DEFAULT_WEIGHTS[EnvironmentType.DEPOSITO_SOTTERRANEO.value]
    # Ambiente caldo-umido → Brimblecombe attivo
    val = ri_insetti(bad_features, codex, w)
    assert val > 5.0  # ben sopra zero


def test_ri_muffa_threshold_alignment(codex, bad_features):
    from app.core.constants import DEFAULT_WEIGHTS
    w = DEFAULT_WEIGHTS[EnvironmentType.DEPOSITO_SOTTERRANEO.value]
    val = ri_muffa(bad_features, codex, w)
    # 2000h/anno = ~22.8% normalizzato → ben sopra critica (5%)
    assert val > RI_THRESHOLDS["RI_Muffa"]["critica"]


def test_ri_foto_pigmenti_sensitivity(good_features):
    """A parità di dose, pigmenti fotosensibili → ΔE* maggiore."""
    from app.core.constants import DEFAULT_WEIGHTS
    w = DEFAULT_WEIGHTS[EnvironmentType.BIBLIOTECA.value]
    f = RiskFeatures(**{**good_features.__dict__, "lux_cumulati_5anni": 5.0e6})
    ms_normal = ManuscriptStatic(pH=6.0, DP0=1200, inchiostro_ferro_gallico=False,
                                  pigmenti_fotosensibili=False, fragilita=0)
    ms_photo = ManuscriptStatic(**{**ms_normal.__dict__, "pigmenti_fotosensibili": True})
    assert ri_fotodeterioramento(f, ms_photo, w) > ri_fotodeterioramento(f, ms_normal, w)


# ---------- RI_Totale e severità -----------------------------------------------


def test_ri_totale_bounds():
    assert ri_totale(0, 0, 0, 0) == 0.0
    assert ri_totale(100, 100, 100, 100) == 100.0
    # Combinazione lineare 0.5/0.1/0.25/0.15
    assert math.isclose(ri_totale(80, 0, 0, 0), 40.0, abs_tol=0.01)


def test_severity_mapping():
    assert severity_from_RI_totale(10.0) == "ottimale"
    assert severity_from_RI_totale(25.0) == "accettabile"
    assert severity_from_RI_totale(40.0) == "attenzione"
    assert severity_from_RI_totale(60.0) == "critico"


def test_severity_at_thresholds():
    """Sui bordi inferiori: il livello deve essere già il successivo."""
    att = RI_THRESHOLDS["RI_Totale"]["attenzione"]
    crit = RI_THRESHOLDS["RI_Totale"]["critica"]
    assert severity_from_RI_totale(att) == "attenzione"
    assert severity_from_RI_totale(crit) == "critico"


# ---------- Engine pubblico -----------------------------------------------------


def test_compute_all_indices_keys(good_features, codex):
    out = compute_all_indices(good_features, codex, EnvironmentType.ARMADIO_CHIUSO)
    expected = {
        "RI_Chimico", "RI_Meccanico", "RI_Insetti", "RI_Muffa",
        "RI_Fotodeterioramento", "RI_Totale", "severity",
    }
    assert set(out.keys()) == expected


def test_compute_indices_good_vs_bad(good_features, bad_features, codex):
    out_good = compute_all_indices(good_features, codex, EnvironmentType.ARMADIO_CHIUSO)
    out_bad = compute_all_indices(bad_features, codex, EnvironmentType.DEPOSITO_SOTTERRANEO)
    assert out_bad["RI_Totale"] > out_good["RI_Totale"]
    assert out_bad["severity"] in ("attenzione", "critico")
    assert out_good["severity"] in ("ottimale", "accettabile")


def test_weights_override_changes_result(good_features, codex):
    """Override dei pesi a runtime → cambia almeno un RI elementare."""
    base = compute_all_indices(good_features, codex, EnvironmentType.BIBLIOTECA)
    overridden = compute_all_indices(
        good_features, codex, EnvironmentType.BIBLIOTECA,
        weights_override={k: 1.0 for k in (
            "T_media_24h", "RH_media_30gg", "dT_24h", "dRH_24h",
            "illuminamento", "PM_VOC", "gradiente_verticale_T",
            "rischio_muffa_LIM", "rischio_insetti",
        )},
    )
    # Almeno uno dei valori deve cambiare (anche di poco)
    diffs = [abs(base[k] - overridden[k]) for k in ("RI_Chimico", "RI_Insetti", "RI_Muffa")]
    assert max(diffs) > 1e-6


# ---------- aggregate_features --------------------------------------------------


def test_aggregate_features_empty():
    f = aggregate_features([])
    assert f.T_media_24h == 20.0  # default neutro


def test_aggregate_features_basic():
    samples = [
        {"T": 20 + 0.01 * i, "RH": 50, "lux": 100 if i % 24 < 8 else 0,
         "VOC": 200, "PM10": 10}
        for i in range(720)  # 30 giorni × 24h
    ]
    f = aggregate_features(samples)
    assert 19.0 < f.T_media_30gg < 28.0
    assert f.RH_media_30gg == 50.0
    assert f.lux_medio == 100.0
    assert f.lux_cumulati_5anni > 0
