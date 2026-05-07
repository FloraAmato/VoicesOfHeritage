# VoH — Voices of Heritage

Prototipo di **dashboard di conservazione preventiva per manoscritti antichi**,
sviluppato per il progetto VoH (CeRICT — Conservatorio di Benevento, Task
4.2.2 / 4.2.3 del D4.2.2).

L'applicazione integra:

- **acquisizione** dati ambientali simulati dal sensore multiparametrico
  artunified (T, RH, lux, UV, PM2.5, PM10, VOC, CO₂);
- **caratterizzazione codicologica** del manufatto (questionario VoH —
  Allegato A del D4.2.2.2);
- **calcolo degli indici di rischio** (Michalski–Verticchio + Brimblecombe +
  Sedlbauer + EN 15757 + ΔE* fotodeterioramento) modulati dalla **matrice pesi
  ambiente-dipendente** (Tab.3);
- **pipeline diagnostica** (DBSCAN su feature ambientali finestrate, 4
  cluster: sano / primo degrado / accentuato / pre-fault);
- **pipeline prognostica** (GradientBoosting su feature finestrate; opzionale
  Bi-LSTM con TF) con **conformal prediction** α=0.9 sulla stima del RUT-A;
- **motore di alert** a 4 livelli (INFO / MEDIA / ALTA / CRITICA) con
  **raccomandazioni operative** strutturate in 3 sezioni;
- **dashboard React** con 5 viste + simulatore what-if + pannello demo
  scenari A–E + linee guida stampabili.

## Architettura a 3 livelli

```
┌────────────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + Tailwind)                                │
│   • Vista Collezione / Ambiente / Manufatto / Predittiva / Alert   │
│   • Demo Scenarios + Linee Guida                                   │
└────────────────────────────────────────────────────────────────────┘
                              ▲                ▲
                       REST   │       WebSocket│  /ws/telemetry
                              ▼                ▼
┌────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                                 │
│   • risk_indices.py   — formule MV/Brimblecombe/Sedlbauer/EN15757  │
│   • clustering.py     — DBSCAN + relabel + t-SNE                   │
│   • prognostic.py     — GBR + conformal prediction                 │
│   • alerts.py         — severity, deduplicazione, raccomandazioni  │
│   • simulator.py      — generatore artunified per 4 ambienti       │
└────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ telemetrie simulate
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  Livello fisico (simulato): TelemetrySimulator                     │
│   • profili nominali per ciascun ambiente                          │
│   • iniezione scenari A–E (Tab.4)                                  │
└────────────────────────────────────────────────────────────────────┘
```

## Quickstart

### Docker (consigliato)

```bash
docker compose up --build
```

- Backend: <http://localhost:8000/docs>
- Frontend: <http://localhost:5173>

### Locale (senza Docker)

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# In un altro terminale:
cd frontend
npm install
npm run dev
```

## Struttura cartelle

```
.
├── backend/
│   ├── app/
│   │   ├── core/constants.py          # Tab.1 soglie + Tab.3 matrice pesi
│   │   ├── models/schemas.py          # Pydantic: Manuscript, Environment, ...
│   │   ├── services/
│   │   │   ├── risk_indices.py        # 5 RI elementari + RI_Totale
│   │   │   ├── simulator.py           # generatore artunified + scenari A–E
│   │   │   ├── seed_data.py           # 4 ambienti + 8 manoscritti precaricati
│   │   │   ├── store.py               # in-memory ring buffer + alerts
│   │   │   ├── clustering.py          # DBSCAN + t-SNE
│   │   │   ├── prognostic.py          # GBR + conformal
│   │   │   ├── ml_pipeline.py         # train_or_load_all + predict
│   │   │   ├── alerts.py              # severity + raccomandazioni
│   │   │   └── risk_pipeline.py       # orchestrazione RI per manufatto
│   │   ├── api/
│   │   │   ├── routes.py              # REST API
│   │   │   └── websocket.py           # /ws/telemetry + indices_alert_loop
│   │   └── main.py                    # FastAPI app + lifespan
│   ├── config/recommendations.yaml    # regole di raccomandazione
│   ├── data/                          # storici 90gg generati al primo avvio
│   ├── models/                        # *.pkl persistiti
│   └── tests/                         # 47 test pytest
└── frontend/
    └── src/
        ├── api/{client,ws}.ts
        ├── components/{Sidebar,SeverityBadge,KPI}.tsx
        ├── views/
        │   ├── CollectionView.tsx     # KPI + layout planimetrico
        │   ├── EnvironmentView.tsx    # serie temporali + bande soglia + breaches
        │   ├── ManuscriptView.tsx     # scheda + radar 5 RI
        │   ├── PredictiveView.tsx     # traiettoria + RUT-A + what-if + t-SNE
        │   ├── AlertsView.tsx         # gestione alert + raccomandazioni
        │   ├── DemoView.tsx           # 5 scenari A–E
        │   └── GuidelinesView.tsx     # 4 linee guida stampabili
        └── main.tsx, App.tsx
```

## Riferimenti scientifici

Il prototipo implementa fedelmente le formule e le soglie del deliverable:

- **D4.2.2.1** — Caratterizzazione manufatti e questionario codicologico
- **D4.2.2.2** — Modello di rischio Michalski–Verticchio, matrice pesi
  ambiente-dipendente (Tab.3), soglie ambientali (Tab.1), scenari demo
  (Tab.4), linee guida operative (cap. 10), tabella sinottica (Tab.6)

L'architettura predittiva (DBSCAN + Bi-LSTM, conformal prediction) è derivata
dal progetto **EFAISTOS** del Polo P.R.I.D.E. (Test Before Invest, CeRICT),
adattando la semantica delle feature al sensore multiparametrico **artunified**.

## Demo scenari (presentazione)

1. Apri il frontend su <http://localhost:5173>
2. Vai su **Demo Scenarios**
3. Avvia uno scenario A–E:
   - **A — Picco RH** in deposito sotterraneo
   - **B — Oscillazioni T rapide** in sala storica P.T.
   - **C — Saturazione VOC** in armadio chiuso
   - **D — Esposizione luminosa** in biblioteca
   - **E — Stratificazione termica** in sala storica
4. Apri **Vista Ambiente** per osservare l'evoluzione delle telemetrie in
   tempo reale (animazione 30–60 sec grazie al time-compression 10×)
5. Apri **Vista Predittiva** per vedere migrazione cluster e RUT-A scendere
6. Apri **Vista Alert** per vedere l'alert generato + raccomandazioni
7. **Reset** riporta tutto a regime nominale

## Test

```bash
cd backend && python -m pytest -q
# 47 passed
```

Coperti: matrice pesi, soglie, formule indici di rischio (f(pH), Brimblecombe,
Sedlbauer LIM, EN 15757), simulatore (profili, scenari A/C, doppia traccia
sala storica, riproducibilità), API (manoscritti, ambienti, indici, pesi
runtime, what-if, demo trigger).

## Personalizzazione

- **Pesi runtime**: modificabili da `PUT /api/weights/{env_type}` o dalla
  Vista Predittiva. Reset ai default Tab.3 con `POST /api/weights/{env_type}/reset`.
- **Regole alert**: editare `backend/config/recommendations.yaml` (no
  ricompilazione richiesta).
- **Modello prognostico**: `MODEL_TYPE=bilstm` per attivare Bi-LSTM (richiede
  TensorFlow). Default: `gbr` (GradientBoosting).

---

*Sistema VoH — CeRICT — Architettura predittiva derivata da EFAISTOS (Test
Before Invest, Polo P.R.I.D.E.). Sensore artunified multiparametrico.*
