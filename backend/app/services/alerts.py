"""
Motore di alert e raccomandazioni operative.

Trigger di severità (D4.2.2.2 Tab.5 + cap.8):
  INFO    : parametro oltre Accettabile ma entro Attenzione, episodico
  MEDIA   : parametro persistente in Attenzione (>48h), ingresso Cluster 2
  ALTA    : parametro in Critico, ingresso Cluster 3, RUT-A < 30 gg
  CRITICA : RI_Totale > 60%, multi-soglia critica, evidenza biologica

Le raccomandazioni sono caricate da config/recommendations.yaml e selezionate
in base a (tipo_evento, classe_rischio, ambiente, caratteristiche_manufatto).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.core.constants import RI_THRESHOLDS, THRESHOLDS, EnvironmentType
from app.models.schemas import Alert, AlertSeverity, AlertStatus, Manuscript
from app.services.store import store


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "recommendations.yaml"


# ---------------------------------------------------------------------------
# Loader regole
# ---------------------------------------------------------------------------
def load_rules() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f) or {}


_RULES: dict = {}


def reload_rules():
    global _RULES
    _RULES = load_rules()


# ---------------------------------------------------------------------------
# Logica di severity
# ---------------------------------------------------------------------------
def compute_severity(
    indices: dict,
    *,
    persistent_attention: bool = False,
    cluster: int = 0,
    rut_a: float = 9999.0,
) -> Optional[AlertSeverity]:
    """Decide la severità di un evento. None → non genera alert."""
    ri_tot = indices.get("RI_Totale", 0.0)

    # CRITICA: RI > 60%
    if ri_tot >= 60.0:
        return AlertSeverity.CRITICA
    # ALTA: cluster 3, RUT < 30, oppure RI > critica (50%)
    if cluster >= 3 or rut_a < 30.0 or ri_tot >= RI_THRESHOLDS["RI_Totale"]["critica"]:
        return AlertSeverity.ALTA
    # MEDIA: cluster 2 o persistente in attenzione
    if cluster == 2 or persistent_attention:
        return AlertSeverity.MEDIA
    # INFO: oltre attenzione (35%)
    if ri_tot >= RI_THRESHOLDS["RI_Totale"]["attenzione"]:
        return AlertSeverity.INFO
    return None


def detect_trigger(
    manuscript: Manuscript, indices: dict, last_sample: Optional[dict]
) -> tuple[str, float, str]:
    """Identifica la variabile-trigger principale e una sintesi testuale."""
    if last_sample:
        # Cerca la peggiore soglia ambientale violata
        env_type = store.environments[manuscript.ambiente_id].tipo.value
        candidates = [
            ("RH", last_sample.get("RH", 0.0)),
            ("T", last_sample.get("T", 0.0)),
            ("VOC", last_sample.get("VOC", 0.0)),
            ("lux", last_sample.get("lux", 0.0)),
        ]
        for k, v in candidates:
            t = THRESHOLDS.get(k)
            if not t:
                continue
            crit = t["critico"]
            att = t["attenzione"]
            if (att[0] is not None and v < att[0]) or (att[1] is not None and v > att[1]):
                msg = f"{k} fuori soglia di attenzione ({v:.1f})"
                return k, float(v), msg
    # Fallback: l'indice elementare maggiore
    elementary = {
        "RI_Chimico": indices.get("RI_Chimico", 0.0),
        "RI_Insetti": indices.get("RI_Insetti", 0.0),
        "RI_Muffa": indices.get("RI_Muffa", 0.0),
        "RI_Meccanico": indices.get("RI_Meccanico", 0.0) * 10,
        "RI_Fotodet.": indices.get("RI_Fotodeterioramento", 0.0),
    }
    k = max(elementary, key=elementary.get)
    return k, float(elementary[k]), f"{k} elevato ({elementary[k]:.1f})"


# ---------------------------------------------------------------------------
# Pubblicazione alert + notifiche simulate
# ---------------------------------------------------------------------------
NOTIFICATION_CHANNELS = {
    AlertSeverity.INFO: ["in_app"],
    AlertSeverity.MEDIA: ["in_app", "email"],
    AlertSeverity.ALTA: ["in_app", "email", "sms"],
    AlertSeverity.CRITICA: ["in_app", "email", "sms", "phone"],
}


def emit_alert(
    manuscript_id: str,
    severity: AlertSeverity,
    indices: dict,
    trigger_var: str,
    trigger_val: float,
    message: str,
) -> Alert:
    m = store.manuscripts[manuscript_id]
    alert = Alert(
        id=f"AL-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        severity=severity,
        manuscript_id=manuscript_id,
        environment_id=m.ambiente_id,
        trigger_variable=trigger_var,
        trigger_value=trigger_val,
        RI_Totale=indices["RI_Totale"],
        message=message,
        recommendation_id=None,
        status=AlertStatus.APERTO,
        note=None,
    )
    store.add_alert(alert)
    # Notifiche simulate (loggate, non inviate)
    for ch in NOTIFICATION_CHANNELS[severity]:
        store.notifications.append({
            "alert_id": alert.id,
            "channel": ch,
            "timestamp": alert.timestamp.isoformat(),
            "payload": message,
        })
    return alert


# ---------------------------------------------------------------------------
# Raccomandazioni
# ---------------------------------------------------------------------------
def get_recommendations(alert: Alert) -> dict:
    """
    Costruisce un blocco strutturato (azioni immediate / verifiche tecniche /
    piano medio termine) basato su (tipo_evento, ambiente, manufatto).
    """
    if not _RULES:
        reload_rules()

    m = store.manuscripts[alert.manuscript_id]
    env = store.environments[alert.environment_id]
    env_type = env.tipo.value

    # Match: cerca regola che combini env + trigger
    rules = _RULES.get("rules", [])
    matches: List[dict] = []
    for r in rules:
        envs = r.get("environments", [])
        triggers = r.get("triggers", [])
        sev = r.get("severities", [])
        if envs and env_type not in envs:
            continue
        if triggers and alert.trigger_variable not in triggers:
            continue
        if sev and alert.severity.value not in sev:
            continue
        matches.append(r)

    azioni: List[str] = []
    verifiche: List[str] = []
    piano: List[str] = []
    for r in matches:
        azioni.extend(r.get("azioni_immediate", []))
        verifiche.extend(r.get("verifiche_tecniche", []))
        piano.extend(r.get("piano_medio_termine", []))

    # Personalizzazioni testuali in base al manufatto
    azioni = [_render(t, m, alert) for t in azioni]
    verifiche = [_render(t, m, alert) for t in verifiche]
    piano = [_render(t, m, alert) for t in piano]

    if not azioni and not verifiche and not piano:
        # Fallback generico
        azioni = [
            f"Ispezione visiva del manufatto {m.id} ({m.nome})",
            "Verifica funzionamento sistema HVAC dell'ambiente",
        ]
        verifiche = ["Misurazione puntuale parametri critici in 4 punti dell'ambiente"]
        piano = ["Pianificare sopralluogo conservatore"]

    return {
        "azioni_immediate": _dedupe(azioni),
        "verifiche_tecniche": _dedupe(verifiche),
        "piano_medio_termine": _dedupe(piano),
    }


def _render(template: str, m: Manuscript, alert: Alert) -> str:
    return (
        template.replace("{manuscript_id}", m.id)
        .replace("{manuscript_name}", m.nome)
        .replace("{environment_id}", alert.environment_id)
        .replace("{trigger_value}", f"{alert.trigger_value:.1f}")
        .replace("{trigger_variable}", alert.trigger_variable)
    )


def _dedupe(seq: List[str]) -> List[str]:
    seen: set = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
