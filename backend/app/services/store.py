"""
In-memory application store.

Tiene:
  - registry dei TelemetrySimulator per ambiente
  - storico telemetrie (ring buffer per ambiente, capped)
  - manoscritti e ambienti precaricati
  - pesi runtime (override modificabile via PUT /api/weights)
  - alert e notifiche
  - storia degli indici di rischio per manufatto

Decisione progettuale: per la demo non serve un DB. Tutto in memoria, con
persistenza su file solo per lo storico iniziale (CSV) e per i modelli ML
(.pkl). La sostituzione con SQLite/Postgres è banale.
"""

from __future__ import annotations

import threading
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from app.core.constants import DEFAULT_WEIGHTS, EnvironmentType
from app.models.schemas import Alert, Environment, Manuscript
from app.services.seed_data import (
    ENVIRONMENTS,
    MANUSCRIPTS,
    generate_all_histories,
    load_history,
)
from app.services.simulator import (
    SimulatorRegistry,
    TelemetrySimulator,
)


HISTORY_CAP = 12960 * 2  # ~180 giorni a 10 min


class AppStore:
    """Singleton-like store dell'applicazione."""

    def __init__(self):
        self._lock = threading.RLock()
        self.environments: Dict[str, Environment] = {e.id: e for e in ENVIRONMENTS}
        self.manuscripts: Dict[str, Manuscript] = {m.id: m for m in MANUSCRIPTS}
        # Pesi runtime (deep-copy per consentire override senza mutare DEFAULT)
        self.weights: Dict[str, Dict[str, float]] = deepcopy(DEFAULT_WEIGHTS)
        # Telemetrie: ring buffer per ambiente
        self.telemetry: Dict[str, Deque[dict]] = {
            e.id: deque(maxlen=HISTORY_CAP) for e in ENVIRONMENTS
        }
        # Indici di rischio: serie temporale per manuscript_id
        self.indices_history: Dict[str, Deque[dict]] = {
            m.id: deque(maxlen=2000) for m in MANUSCRIPTS
        }
        # Alert e notifiche
        self.alerts: List[Alert] = []
        self.notifications: List[dict] = []
        # Simulator registry
        self.simulators = SimulatorRegistry()
        # Subscribers WebSocket: lista di callback / queue
        self._ws_clients: List = []

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------
    def initialize(self, generate_history_days: int = 90) -> None:
        """Genera storici se non presenti, popola simulator e ring buffers."""
        with self._lock:
            generate_all_histories(days=generate_history_days, force=False)
            for env in self.environments.values():
                # Carica storico in ring buffer
                hist = load_history(env.id)
                self.telemetry[env.id].extend(hist)
                # Crea simulatore live: punto di start = ultimo timestamp + 10 min
                last_ts = (
                    datetime.fromisoformat(hist[-1]["timestamp"]) if hist
                    else datetime.now(timezone.utc)
                )
                sim = TelemetrySimulator(
                    environment_id=env.id,
                    environment_type=env.tipo,
                    seed=hash(env.id) % 1000 + 42,
                    start_time=last_ts,
                )
                self.simulators.register(sim)

    # ------------------------------------------------------------------
    # Pesi runtime
    # ------------------------------------------------------------------
    def get_weights(self, env_type: str) -> Dict[str, float]:
        with self._lock:
            return dict(self.weights[env_type])

    def set_weights(self, env_type: str, new_weights: Dict[str, float]) -> Dict[str, float]:
        with self._lock:
            existing = self.weights.setdefault(env_type, {})
            existing.update({k: float(v) for k, v in new_weights.items()})
            return dict(existing)

    def reset_weights(self, env_type: Optional[str] = None) -> None:
        with self._lock:
            if env_type:
                self.weights[env_type] = deepcopy(DEFAULT_WEIGHTS[env_type])
            else:
                self.weights = deepcopy(DEFAULT_WEIGHTS)

    # ------------------------------------------------------------------
    # Telemetria
    # ------------------------------------------------------------------
    def append_telemetry(self, sample: dict) -> None:
        with self._lock:
            self.telemetry[sample["environment_id"]].append(sample)

    def get_telemetry(
        self, env_id: str, *, limit: Optional[int] = None,
        since: Optional[datetime] = None, quota: Optional[str] = None,
    ) -> List[dict]:
        with self._lock:
            buf = list(self.telemetry[env_id])
        if quota is not None:
            buf = [s for s in buf if s.get("quota") == quota]
        if since is not None:
            iso = since.isoformat()
            buf = [s for s in buf if s["timestamp"] >= iso]
        if limit is not None:
            buf = buf[-limit:]
        return buf

    # ------------------------------------------------------------------
    # Indici di rischio
    # ------------------------------------------------------------------
    def append_indices(self, manuscript_id: str, indices: dict) -> None:
        with self._lock:
            self.indices_history.setdefault(manuscript_id, deque(maxlen=2000)).append(indices)

    def get_indices_history(self, manuscript_id: str, limit: Optional[int] = None) -> List[dict]:
        with self._lock:
            buf = list(self.indices_history.get(manuscript_id, []))
        if limit is not None:
            buf = buf[-limit:]
        return buf

    # ------------------------------------------------------------------
    # Alert
    # ------------------------------------------------------------------
    def add_alert(self, alert: Alert) -> None:
        with self._lock:
            self.alerts.append(alert)

    def list_alerts(self) -> List[Alert]:
        with self._lock:
            return list(self.alerts)

    def update_alert(self, alert_id: str, **fields) -> Optional[Alert]:
        with self._lock:
            for a in self.alerts:
                if a.id == alert_id:
                    for k, v in fields.items():
                        if hasattr(a, k):
                            setattr(a, k, v)
                    return a
        return None


# Singleton
store = AppStore()
