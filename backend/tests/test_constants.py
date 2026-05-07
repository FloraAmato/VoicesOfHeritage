"""Test sulle costanti di dominio (matrice pesi, soglie)."""

from app.core.constants import (
    DEFAULT_WEIGHTS,
    RI_THRESHOLDS,
    THRESHOLDS,
    WEIGHT_VARIABLES,
    EnvironmentType,
)


def test_weights_matrix_has_all_environments():
    """La matrice pesi deve coprire tutti i 4 contesti VoH."""
    expected = {e.value for e in EnvironmentType}
    assert set(DEFAULT_WEIGHTS.keys()) == expected


def test_weights_matrix_has_all_variables():
    """Ogni ambiente deve definire un peso per ciascuna delle 9 variabili."""
    for env, weights in DEFAULT_WEIGHTS.items():
        assert set(weights.keys()) == set(WEIGHT_VARIABLES), f"Mismatch per {env}"
        for var, w in weights.items():
            assert 0.0 <= w <= 1.0, f"Peso fuori range [0,1] per {env}/{var}: {w}"


def test_weights_dominant_variables():
    """
    Le variabili dominanti per contesto (D4.2.2.2 Tab.3) devono avere peso ≥ 0.9.
    """
    armadio = DEFAULT_WEIGHTS[EnvironmentType.ARMADIO_CHIUSO.value]
    assert armadio["PM_VOC"] >= 0.9  # dominante per armadio chiuso

    biblio = DEFAULT_WEIGHTS[EnvironmentType.BIBLIOTECA.value]
    assert biblio["illuminamento"] >= 1.0  # dominante per biblioteca

    deposito = DEFAULT_WEIGHTS[EnvironmentType.DEPOSITO_SOTTERRANEO.value]
    assert deposito["RH_media_30gg"] >= 0.9
    assert deposito["rischio_muffa_LIM"] >= 1.0
    assert deposito["rischio_insetti"] >= 0.9

    sala = DEFAULT_WEIGHTS[EnvironmentType.SALA_STORICA.value]
    assert sala["dT_24h"] >= 0.9
    assert sala["dRH_24h"] >= 1.0
    assert sala["gradiente_verticale_T"] >= 1.0
    assert sala["T_media_24h"] >= 0.8


def test_thresholds_have_4_levels():
    """Ogni parametro deve avere 4 livelli (ottimale/accettabile/attenzione/critico)."""
    expected_levels = {"ottimale", "accettabile", "attenzione", "critico"}
    for param, levels in THRESHOLDS.items():
        assert set(levels.keys()) == expected_levels, f"Livelli mancanti per {param}"


def test_RI_thresholds_ordering():
    """attenzione < critica per tutti gli RI."""
    for ri, th in RI_THRESHOLDS.items():
        assert th["attenzione"] < th["critica"], f"Ordine errato per {ri}"
