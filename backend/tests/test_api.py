"""Smoke test sulle API REST principali (manoscritti, ambienti, indici, pesi)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    # Lifespan setup è incluso in TestClient context manager
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_manuscripts(client):
    r = client.get("/api/manuscripts")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 8  # 2 per ogni ambiente
    ids = {m["id"] for m in data}
    assert "MS-5463" in ids and "MS-3341" in ids


def test_get_manuscript_detail(client):
    r = client.get("/api/manuscripts/MS-5463")
    assert r.status_code == 200
    assert r.json()["nome"].startswith("Codex Beneventanus")


def test_get_manuscript_404(client):
    r = client.get("/api/manuscripts/MS-XXXX")
    assert r.status_code == 404


def test_list_environments(client):
    r = client.get("/api/environments")
    assert r.status_code == 200
    assert len(r.json()) == 4


def test_telemetry_history(client):
    r = client.get("/api/environments/ENV-DEP-01/telemetry?limit=100")
    assert r.status_code == 200
    data = r.json()
    assert 1 <= len(data) <= 100
    sample = data[0]
    assert {"timestamp", "T", "RH", "lux", "VOC"}.issubset(sample.keys())


def test_indices_current(client):
    r = client.get("/api/manuscripts/MS-5463/indices")
    assert r.status_code == 200
    body = r.json()
    expected = {
        "RI_Chimico", "RI_Meccanico", "RI_Insetti", "RI_Muffa",
        "RI_Fotodeterioramento", "RI_Totale", "severity",
    }
    assert expected.issubset(body.keys())
    assert body["severity"] in ("ottimale", "accettabile", "attenzione", "critico")


def test_weights_get_and_put(client):
    # Get
    r = client.get("/api/weights/biblioteca_consultazione")
    assert r.status_code == 200
    weights = r.json()["weights"]
    assert weights["illuminamento"] == 1.0

    # Put: modifica peso illuminamento
    payload = {**weights, "illuminamento": 0.5}
    r = client.put("/api/weights/biblioteca_consultazione", json=payload)
    assert r.status_code == 200
    assert r.json()["illuminamento"] == 0.5

    # Reset
    r = client.post("/api/weights/biblioteca_consultazione/reset")
    assert r.status_code == 200
    assert r.json()["illuminamento"] == 1.0


def test_weights_validation_rejects_out_of_range(client):
    bad = {"illuminamento": 1.5}
    r = client.put("/api/weights/biblioteca_consultazione", json=bad)
    assert r.status_code == 400


def test_thresholds(client):
    r = client.get("/api/thresholds")
    assert r.status_code == 200
    body = r.json()
    assert "T" in body["environmental"]
    assert body["environmental"]["T"]["ottimale"] == [16.0, 20.0]
    assert "RI_Totale" in body["risk_indices"]


def test_dashboard_summary(client):
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 8
    assert len(body["manuscripts"]) == 8


def test_whatif_changes_results(client):
    r0 = client.get("/api/manuscripts/MS-5463/indices")
    base = r0.json()
    r1 = client.post(
        "/api/manuscripts/MS-5463/whatif",
        json={"T_set": 28.0, "RH_set": 80.0},
    )
    assert r1.status_code == 200
    out = r1.json()
    # Il what-if non muta lo store: la chiamata indices deve restare invariata
    r2 = client.get("/api/manuscripts/MS-5463/indices")
    assert r2.json() == base


def test_demo_scenario_trigger(client):
    r = client.post(
        "/api/demo/scenario",
        json={
            "environment_id": "ENV-DEP-01",
            "scenario": "A",
            "duration_hours": 48,
        },
    )
    assert r.status_code == 200
    assert r.json()["scenario"] == "A"

    r = client.post("/api/demo/reset")
    assert r.status_code == 200
